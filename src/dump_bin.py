# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import abc
import shutil
import traceback
from pathlib import Path
from typing import Iterable, List, Union
from functools import partial
from concurrent.futures import ThreadPoolExecutor, as_completed, ProcessPoolExecutor

import fire
import numpy as np
import pandas as pd
from tqdm import tqdm
from loguru import logger


class DumpDataBase:
    INSTRUMENTS_START_FIELD = "start_datetime"
    INSTRUMENTS_END_FIELD = "end_datetime"
    CALENDARS_DIR_NAME = "calendars"
    FEATURES_DIR_NAME = "features"
    INSTRUMENTS_DIR_NAME = "instruments"
    DUMP_FILE_SUFFIX = ".bin"
    DAILY_FORMAT = "%Y-%m-%d"
    HIGH_FREQ_FORMAT = "%Y-%m-%d %H:%M:%S"
    INSTRUMENTS_SEP = "\t"
    INSTRUMENTS_FILE_NAME = "all.txt"
    SAVE_INST_FIELD = "save_inst"

    UPDATE_MODE = "update"
    ALL_MODE = "all"

    def __init__(
        self,
        csv_path: str,
        qlib_dir: str,
        backup_dir: str = None,
        freq: str = "day",
        max_workers: int = 16,
        date_field_name: str = "date",
        file_suffix: str = ".csv",
        symbol_field_name: str = "symbol",
        exclude_fields: str = "",
        include_fields: str = "",
        limit_nums: int = None,
        inst_prefix: str = "",
        fund_to_specify_date: str = "",
    ):
        """

        Parameters
        ----------
        csv_path: str
            stock data path or directory
        qlib_dir: str
            qlib(dump) data director
        backup_dir: str, default None
            if backup_dir is not None, backup qlib_dir to backup_dir
        freq: str, default "day"
            transaction frequency
        max_workers: int, default None
            number of threads
        date_field_name: str, default "date"
            the name of the date field in the csv
        file_suffix: str, default ".csv"
            file suffix
        symbol_field_name: str, default "symbol"
            symbol field name
        include_fields: tuple
            dump fields
        exclude_fields: tuple
            fields not dumped
        limit_nums: int
            Use when debugging, default None
        inst_prefix: str
            add a column to the instruments file and record the saved instrument name,
            the US stock code contains "PRN", and the directory cannot be created on Windows system, use the "_" prefix.
        fund_to_specify_date: str
            specify a fund to use its trading days as the common trading days to prevent the days poluteed by some funds
        """
        csv_path = Path(csv_path).expanduser()
        if isinstance(exclude_fields, str):
            exclude_fields = exclude_fields.split(",")
        if isinstance(include_fields, str):
            include_fields = include_fields.split(",")
        self._exclude_fields = tuple(filter(lambda x: len(x) > 0, map(str.strip, exclude_fields)))
        self._include_fields = tuple(filter(lambda x: len(x) > 0, map(str.strip, include_fields)))
        self._inst_prefix = inst_prefix.strip()
        self.fund_to_specify_date = fund_to_specify_date.strip()
        self.file_suffix = file_suffix
        self.symbol_field_name = symbol_field_name
        self.csv_files = sorted(csv_path.glob(f"*{self.file_suffix}") if csv_path.is_dir() else [csv_path])
        if limit_nums is not None:
            self.csv_files = self.csv_files[: int(limit_nums)]
        self.qlib_dir = Path(qlib_dir).expanduser()
        self.backup_dir = backup_dir if backup_dir is None else Path(backup_dir).expanduser()
        if backup_dir is not None:
            self._backup_qlib_dir(Path(backup_dir).expanduser())

        self.freq = freq
        self.calendar_format = self.DAILY_FORMAT if self.freq == "day" else self.HIGH_FREQ_FORMAT

        self.works = max_workers
        self.date_field_name = date_field_name

        self._calendars_dir = self.qlib_dir.joinpath(self.CALENDARS_DIR_NAME)
        self._features_dir = self.qlib_dir.joinpath(self.FEATURES_DIR_NAME)
        self._instruments_dir = self.qlib_dir.joinpath(self.INSTRUMENTS_DIR_NAME)

        self._calendars_list = []

        self._mode = self.ALL_MODE
        self._kwargs = {}

    def _backup_qlib_dir(self, target_dir: Path):
        shutil.copytree(str(self.qlib_dir.resolve()), str(target_dir.resolve()))

    def _format_datetime(self, datetime_d: [str, pd.Timestamp]):
        datetime_d = pd.Timestamp(datetime_d)
        return datetime_d.strftime(self.calendar_format)

    def _get_date(
        self, file_or_df: [Path, pd.DataFrame], *, is_begin_end: bool = False, as_set: bool = False
    ) -> Iterable[pd.Timestamp]:
        if not isinstance(file_or_df, pd.DataFrame):
            df = self._get_source_data(file_or_df)
        else:
            df = file_or_df
        if df.empty or self.date_field_name not in df.columns.tolist():
            _calendars = pd.Series()
        else:
            _calendars = df[self.date_field_name]

        if is_begin_end and as_set:
            return (_calendars.min(), _calendars.max()), set(_calendars)
        elif is_begin_end:
            return _calendars.min(), _calendars.max()
        elif as_set:
            return set(_calendars)
        else:
            return _calendars.tolist()

    def _get_source_data(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_csv(str(file_path.resolve()), low_memory=False)
        df[self.date_field_name] = df[self.date_field_name].astype(str).astype(np.datetime64)
        # df.drop_duplicates([self.date_field_name], inplace=True)
        return df

    def get_symbol_from_file(self, file_path: Path) -> str:
        return file_path.name[: -len(self.file_suffix)].strip().lower()

    def get_dump_fields(self, df_columns: Iterable[str]) -> Iterable[str]:
        return (
            self._include_fields
            if self._include_fields
            else set(df_columns) - set(self._exclude_fields)
            if self._exclude_fields
            else df_columns
        )

    @staticmethod
    def _read_calendars(calendar_path: Path) -> List[pd.Timestamp]:
        return sorted(
            map(
                pd.Timestamp,
                pd.read_csv(calendar_path, header=None).loc[:, 0].tolist(),
            )
        )

    def _read_instruments(self, instrument_path: Path) -> pd.DataFrame:
        df = pd.read_csv(
            instrument_path,
            sep=self.INSTRUMENTS_SEP,
            names=[
                self.symbol_field_name,
                self.INSTRUMENTS_START_FIELD,
                self.INSTRUMENTS_END_FIELD,
                self.SAVE_INST_FIELD,
            ],
        )

        return df

    def save_calendars(self, calendars_data: list):
        self._calendars_dir.mkdir(parents=True, exist_ok=True)
        calendars_path = str(self._calendars_dir.joinpath(f"{self.freq}.txt").expanduser().resolve())
        result_calendars_list = list(map(lambda x: self._format_datetime(x), calendars_data))
        np.savetxt(calendars_path, result_calendars_list, fmt="%s", encoding="utf-8")

    def save_instruments(self, instruments_data: Union[list, pd.DataFrame]):
        self._instruments_dir.mkdir(parents=True, exist_ok=True)
        instruments_path = str(self._instruments_dir.joinpath(self.INSTRUMENTS_FILE_NAME).resolve())
        if isinstance(instruments_data, pd.DataFrame):
            _df_fields = [self.symbol_field_name, self.INSTRUMENTS_START_FIELD, self.INSTRUMENTS_END_FIELD]
            if self._inst_prefix:
                _df_fields.append(self.SAVE_INST_FIELD)
                instruments_data[self.SAVE_INST_FIELD] = instruments_data[self.symbol_field_name].apply(
                    lambda x: f"{self._inst_prefix}{x}"
                )
            instruments_data = instruments_data.loc[:, _df_fields]
            instruments_data.to_csv(instruments_path, header=False, sep=self.INSTRUMENTS_SEP)
        else:
            np.savetxt(instruments_path, instruments_data, fmt="%s", encoding="utf-8")

    def data_merge_calendar(self, df: pd.DataFrame, calendars_list: List[pd.Timestamp]) -> pd.DataFrame:
        # calendars
        calendars_df = pd.DataFrame(data=calendars_list, columns=[self.date_field_name])
        calendars_df[self.date_field_name] = calendars_df[self.date_field_name].astype(np.datetime64)
        cal_df = calendars_df[
            (calendars_df[self.date_field_name] >= df[self.date_field_name].min())
            & (calendars_df[self.date_field_name] <= df[self.date_field_name].max())
        ]
        # align index
        cal_df.set_index(self.date_field_name, inplace=True)
        df.set_index(self.date_field_name, inplace=True)
        r_df = df.reindex(cal_df.index)
        return r_df

    @staticmethod
    def get_datetime_index(df: pd.DataFrame, calendar_list: List[pd.Timestamp]) -> int:
        return calendar_list.index(df.index.min())

    def _data_to_bin(self, df: pd.DataFrame, calendar_list: List[pd.Timestamp], features_dir: Path):
        if df.empty:
            logger.warning(f"{features_dir.name} data is None or empty")
            return
        # align index
        _df = self.data_merge_calendar(df, self._calendars_list)
        try:
            date_index = self.get_datetime_index(_df, calendar_list)
        except:
            return
        for field in self.get_dump_fields(_df.columns):
            bin_path = features_dir.joinpath(f"{field}.{self.freq}{self.DUMP_FILE_SUFFIX}")
            if field not in _df.columns:
                continue
            if self._mode == self.UPDATE_MODE:
                # update
                with bin_path.open("ab") as fp:
                    np.array(_df[field]).astype("<f").tofile(fp)
            elif self._mode == self.ALL_MODE:
                np.hstack([date_index, _df[field]]).astype("<f").tofile(str(bin_path.resolve()))
            else:
                raise ValueError(f"{self._mode} cannot support!")

    def _dump_bin(self, file_or_data: [Path, pd.DataFrame], calendar_list: List[pd.Timestamp]):
        if isinstance(file_or_data, pd.DataFrame):
            if file_or_data.empty:
                return
            code = file_or_data.iloc[0][self.symbol_field_name].lower()
            df = file_or_data
        elif isinstance(file_or_data, Path):
            code = self.get_symbol_from_file(file_or_data)
            df = self._get_source_data(file_or_data)
        else:
            raise ValueError(f"not support {type(file_or_data)}")
        if df is None or df.empty:
            logger.warning(f"{code} data is None or empty")
            return
        # features save dir
        code = self._inst_prefix + code if self._inst_prefix else code
        features_dir = self._features_dir.joinpath(code)
        features_dir.mkdir(parents=True, exist_ok=True)
        self._data_to_bin(df, calendar_list, features_dir)

    @abc.abstractmethod
    def dump(self):
        raise NotImplementedError("dump not implemented!")

    def __call__(self, *args, **kwargs):
        self.dump()


class DumpDataAll(DumpDataBase):
    def _get_all_date(self):
        logger.info("start get all date......")
        all_datetime = set()
        date_range_list = []
        _fun = partial(self._get_date, as_set=True, is_begin_end=True)
        with tqdm(total=len(self.csv_files)) as p_bar:
            with ProcessPoolExecutor(max_workers=self.works) as executor:
                for file_path, ((_begin_time, _end_time), _set_calendars) in zip(
                    self.csv_files, executor.map(_fun, self.csv_files)
                ):
                    if self.fund_to_specify_date in str(file_path): # empty string always in all strings
                        all_datetime = all_datetime | _set_calendars
                    
                    if isinstance(_begin_time, pd.Timestamp) and isinstance(_end_time, pd.Timestamp):
                        _begin_time = self._format_datetime(_begin_time)
                        _end_time = self._format_datetime(_end_time)
                        symbol = self.get_symbol_from_file(file_path)
                        _inst_fields = [symbol.upper(), _begin_time, _end_time]
                        if self._inst_prefix:
                            _inst_fields.append(self._inst_prefix + symbol.upper())
                        date_range_list.append(f"{self.INSTRUMENTS_SEP.join(_inst_fields)}")
                    p_bar.update()
        self._kwargs["all_datetime_set"] = all_datetime
        self._kwargs["date_range_list"] = date_range_list
        logger.info("end of get all date.\n")

    def _dump_calendars(self):
        logger.info("start dump calendars......")
        self._calendars_list = sorted(map(pd.Timestamp, self._kwargs["all_datetime_set"]))
        self.save_calendars(self._calendars_list)
        logger.info("end of calendars dump.\n")

    def _dump_instruments(self):
        logger.info("start dump instruments......")
        self.save_instruments(self._kwargs["date_range_list"])
        logger.info("end of instruments dump.\n")

    def _dump_features(self):
        logger.info("start dump features......")
        _dump_func = partial(self._dump_bin, calendar_list=self._calendars_list)
        with tqdm(total=len(self.csv_files)) as p_bar:
            with ProcessPoolExecutor(max_workers=self.works) as executor:
                for _ in executor.map(_dump_func, self.csv_files):
                    p_bar.update()

        logger.info("end of features dump.\n")

    def dump(self):
        self._get_all_date()
        self._dump_calendars()
        self._dump_instruments()
        self._dump_features()


class DumpDataFix(DumpDataAll):
    def _dump_instruments(self):
        logger.info("start dump instruments......")
        _fun = partial(self._get_date, is_begin_end=True)
        new_stock_files = sorted(filter(lambda x: x.name not in self._old_instruments, self.csv_files))
        with tqdm(total=len(new_stock_files)) as p_bar:
            with ProcessPoolExecutor(max_workers=self.works) as execute:
                for file_path, (_begin_time, _end_time) in zip(new_stock_files, execute.map(_fun, new_stock_files)):
                    if isinstance(_begin_time, pd.Timestamp) and isinstance(_end_time, pd.Timestamp):
                        symbol = self.get_symbol_from_file(file_path).upper()
                        _dt_map = self._old_instruments.setdefault(symbol, dict())
                        _dt_map[self.INSTRUMENTS_START_FIELD] = self._format_datetime(_begin_time)
                        _dt_map[self.INSTRUMENTS_END_FIELD] = self._format_datetime(_end_time)
                    p_bar.update()
        _inst_df = pd.DataFrame.from_dict(self._old_instruments, orient="index")
        _inst_df.index.names = [self.symbol_field_name]
        self.save_instruments(_inst_df.reset_index())
        logger.info("end of instruments dump.\n")

    def dump(self):
        self._calendars_list = self._read_calendars(self._calendars_dir.joinpath(f"{self.freq}.txt"))
        # noinspection PyAttributeOutsideInit
        self._old_instruments = (
            self._read_instruments(self._instruments_dir.joinpath(self.INSTRUMENTS_FILE_NAME))
            .set_index([self.symbol_field_name])
            .to_dict(orient="index")
        )  # type: dict
        self._dump_instruments()
        self._dump_features()


class DumpDataUpdate(DumpDataBase):
    def __init__(
        self,
        csv_path: str,
        qlib_dir: str,
        backup_dir: str = None,
        freq: str = "day",
        max_workers: int = 16,
        date_field_name: str = "date",
        file_suffix: str = ".csv",
        symbol_field_name: str = "symbol",
        exclude_fields: str = "",
        include_fields: str = "",
        limit_nums: int = None,
    ):
        """

        Parameters
        ----------
        csv_path: str
            stock data path or directory
        qlib_dir: str
            qlib(dump) data director
        backup_dir: str, default None
            if backup_dir is not None, backup qlib_dir to backup_dir
        freq: str, default "day"
            transaction frequency
        max_workers: int, default None
            number of threads
        date_field_name: str, default "date"
            the name of the date field in the csv
        file_suffix: str, default ".csv"
            file suffix
        symbol_field_name: str, default "symbol"
            symbol field name
        include_fields: tuple
            dump fields
        exclude_fields: tuple
            fields not dumped
        limit_nums: int
            Use when debugging, default None
        """
        super().__init__(
            csv_path,
            qlib_dir,
            backup_dir,
            freq,
            max_workers,
            date_field_name,
            file_suffix,
            symbol_field_name,
            exclude_fields,
            include_fields,
        )
        self._mode = self.UPDATE_MODE
        self._old_calendar_list = self._read_calendars(self._calendars_dir.joinpath(f"{self.freq}.txt"))
        self._update_instruments = self._read_instruments(
            self._instruments_dir.joinpath(self.INSTRUMENTS_FILE_NAME)
        ).to_dict(
            orient="index"
        )  # type: dict

        # load all csv files
        self._all_data = self._load_all_source_data()  # type: pd.DataFrame
        self._update_calendars = sorted(
            filter(lambda x: x > self._old_calendar_list[-1], self._all_data[self.date_field_name].unique())
        )
        self._new_calendar_list = self._old_calendar_list + self._update_calendars

    def _load_all_source_data(self):
        # NOTE: Need more memory
        logger.info("start load all source data....")
        all_df = []

        def _read_csv(file_path: Path):
            if self._include_fields:
                _df = pd.read_csv(file_path, usecols=self._include_fields)
            else:
                _df = pd.read_csv(file_path)
            if self.symbol_field_name not in _df.columns:
                _df[self.symbol_field_name] = self.get_symbol_from_file(file_path)
            return _df

        with tqdm(total=len(self.csv_files)) as p_bar:
            with ThreadPoolExecutor(max_workers=self.works) as executor:
                for df in executor.map(_read_csv, self.csv_files):
                    if df:
                        all_df.append(df)
                    p_bar.update()

        logger.info("end of load all data.\n")
        return pd.concat(all_df, sort=False)

    def _dump_calendars(self):
        pass

    def _dump_instruments(self):
        pass

    def _dump_features(self):
        logger.info("start dump features......")
        error_code = {}
        with ProcessPoolExecutor(max_workers=self.works) as executor:
            futures = {}
            for _code, _df in self._all_data.groupby(self.symbol_field_name):
                _code = str(_code).upper()
                _start, _end = self._get_date(_df, is_begin_end=True)
                if not (isinstance(_start, pd.Timestamp) and isinstance(_end, pd.Timestamp)):
                    continue
                if _code in self._update_instruments:
                    self._update_instruments[_code]["end_time"] = _end
                    futures[executor.submit(self._dump_bin, _df, self._update_calendars)] = _code
                else:
                    # new stock
                    _dt_range = self._update_instruments.setdefault(_code, dict())
                    _dt_range["start_time"] = _start
                    _dt_range["end_time"] = _end
                    futures[executor.submit(self._dump_bin, _df, self._new_calendar_list)] = _code

            for _future in tqdm(as_completed(futures)):
                try:
                    _future.result()
                except Exception:
                    error_code[futures[_future]] = traceback.format_exc()
            logger.info(f"dump bin errors： {error_code}")

        logger.info("end of features dump.\n")

    def dump(self):
        self.save_calendars(self._new_calendar_list)
        self._dump_features()
        self.save_instruments(pd.DataFrame.from_dict(self._update_instruments, orient="index"))


if __name__ == "__main__":
    fire.Fire({"dump_all": DumpDataAll, "dump_fix": DumpDataFix, "dump_update": DumpDataUpdate})
