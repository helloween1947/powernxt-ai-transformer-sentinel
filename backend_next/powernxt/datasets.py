"""Bounded CSV/XLSX import with explicit column mapping and timestamps."""
import csv
import io
import zipfile
from xml.etree.ElementTree import ParseError
from openpyxl.utils.exceptions import InvalidFileException
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from openpyxl import load_workbook
from pydantic import ValidationError
from .schemas import CHANNELS, Measurements

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 20000

class DatasetError(ValueError):
    pass

def parse_dataset(data, filename, mapping, timezone_name='UTC', sheet=None):
    if not data or len(data) > MAX_BYTES:
        raise DatasetError('File must contain data and be at most 10 MiB.')
    try:
        zone = ZoneInfo(timezone_name)
    except (ValueError, KeyError) as exc:
        raise DatasetError('Unknown dataset timezone.') from exc
    if not isinstance(mapping, dict) or any(key not in (*CHANNELS, 'timestamp') or not isinstance(value, str) for key, value in mapping.items()):
        raise DatasetError('Column mapping must map canonical channel names to header strings.')
    suffix = filename.lower().rsplit('.', 1)[-1]
    workbook = None
    try:
        if suffix == 'csv':
            rows = csv.reader(io.StringIO(data.decode('utf-8-sig')))
        elif suffix == 'xlsx':
            workbook = bounded_workbook(data)
            if sheet and sheet not in workbook.sheetnames:
                raise DatasetError('Selected worksheet does not exist.')
            worksheet = workbook[sheet] if sheet else workbook.active
            if worksheet.max_column and worksheet.max_column > 100:
                raise DatasetError('Use a worksheet with at most 100 columns.')
            rows = worksheet.iter_rows(values_only=True)
        else:
            raise DatasetError('Only UTF-8 CSV and XLSX files are supported.')
        header = [str(value).strip() if value is not None else '' for value in next(rows, [])]
        if not header or len(header) > 100 or any(not h for h in header) or len(set(header)) != len(header):
            raise DatasetError('Headers must be present, nonempty and unique (maximum 100 columns).')
        selected = mapping or {key: key for key in ('timestamp', *CHANNELS) if key in header}
        if 'timestamp' not in selected or not set(selected).intersection(CHANNELS):
            raise DatasetError('Map a timestamp and at least one measurement channel; timestamps cannot be invented.')
        if any(value not in header for value in selected.values()) or len(set(selected.values())) != len(selected):
            raise DatasetError('Mapped headers must exist and cannot be reused.')
        indexes = {key: header.index(value) for key, value in selected.items()}
        result = []
        seen = set()
        for line, row in enumerate(rows, 2):
            if line > MAX_ROWS + 1:
                raise DatasetError(f'Maximum {MAX_ROWS} rows per upload.')
            if all(value in (None, '') for value in row):
                continue
            if len(row) != len(header):
                raise DatasetError(f'Row {line}: number of cells does not match the header.')
            try:
                raw_time = row[indexes['timestamp']]
                dt = raw_time if isinstance(raw_time, datetime) else datetime.fromisoformat(str(raw_time).strip().replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    # Ambiguous DST wall-clock timestamps require an explicit offset.
                    first, second = dt.replace(tzinfo=zone, fold=0), dt.replace(tzinfo=zone, fold=1)
                    if first.utcoffset() != second.utcoffset():
                        raise ValueError('Ambiguous/nonexistent local time; include a UTC offset.')
                    dt = first
                dt = dt.astimezone(timezone.utc)
                timestamp = dt.isoformat()
                if dt > datetime.now(timezone.utc):
                    raise ValueError('Future timestamp is not an observed measurement.')
                if timestamp in seen:
                    raise ValueError('Duplicate measurement timestamp.')
                values = {channel: (None if channel not in indexes or row[indexes[channel]] in (None, '') else row[indexes[channel]]) for channel in CHANNELS}
                measurements = Measurements.model_validate(values).model_dump()
            except (ValueError, TypeError, ValidationError) as exc:
                raise DatasetError(f'Row {line}: {exc}') from exc
            seen.add(timestamp)
            result.append({'timestamp': timestamp, 'measurements': measurements})
        if not result:
            raise DatasetError('No measurement rows found.')
        return sorted(result, key=lambda row: row['timestamp'])
    except DatasetError:
        raise
    except (UnicodeDecodeError, zipfile.BadZipFile, OSError, csv.Error, KeyError, ParseError, InvalidFileException, ValueError) as exc:
        raise DatasetError('The file is not a readable UTF-8 CSV or XLSX workbook.') from exc
    finally:
        if workbook:
            workbook.close()


def bounded_workbook(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > 1000 or sum(f.file_size for f in archive.infolist()) > 50 * 1024 * 1024:
            raise DatasetError('Expanded workbook exceeds the import limit.')
    return load_workbook(io.BytesIO(data), read_only=True, data_only=True)


def dataset_headers(data, filename, sheet=None):
    if not data or len(data) > MAX_BYTES:
        raise DatasetError('File must contain data and be at most 10 MiB.')
    workbook = None
    try:
        if filename.lower().endswith('.csv'):
            header = next(csv.reader(io.StringIO(data.decode('utf-8-sig'))), [])
            sheets = []
        elif filename.lower().endswith('.xlsx'):
            workbook = bounded_workbook(data)
            sheets = workbook.sheetnames
            if sheet and sheet not in sheets:
                raise DatasetError('Selected worksheet does not exist.')
            worksheet = workbook[sheet] if sheet else workbook.active
            if worksheet.max_column and worksheet.max_column > 100:
                raise DatasetError('Use a worksheet with at most 100 columns.')
            header = next(worksheet.iter_rows(values_only=True), [])
        else:
            raise DatasetError('Only UTF-8 CSV and XLSX files are supported.')
        header = [str(value).strip() if value is not None else '' for value in header]
        if not header or len(header) > 100 or any(not h for h in header) or len(set(header)) != len(header):
            raise DatasetError('Headers must be nonempty and unique (maximum 100 columns).')
        return {'columns': header, 'sheets': sheets, 'selected_sheet': worksheet.title if workbook else None}
    except DatasetError:
        raise
    except (UnicodeDecodeError, zipfile.BadZipFile, OSError, csv.Error, KeyError, ParseError, InvalidFileException, ValueError) as exc:
        raise DatasetError('The file is not a readable UTF-8 CSV or XLSX workbook.') from exc
    finally:
        if workbook:
            workbook.close()
