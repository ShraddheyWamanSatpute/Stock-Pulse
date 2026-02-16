"""
NSE Bhavcopy extractor.

Downloads daily NSE Bhavcopy CSV files and extracts price/volume data
for all listed equity stocks. Also handles delivery data from NSE.

Bhavcopy URL pattern:
    https://archives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MMM}/cm{DDMMMYYYY}bhav.csv.zip

Delivery data URL pattern:
    https://archives.nseindia.com/products/content/sec_bhavdata_full_{DDMMYYYY}.csv
"""

import csv
import io
import logging
import os
import tempfile
import zipfile
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

from .base_extractor import BaseExtractor
from ..config.source_config import NSE_BHAVCOPY_CONFIG, NSE_DELIVERY_CONFIG
from ..models.extraction_models import ExtractionRecord, ExtractionStatus, StockDataRecord

logger = logging.getLogger(__name__)

# Mapping of month numbers to 3-letter uppercase abbreviations (NSE format)
MONTH_MAP = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}


class NSEBhavcopyExtractor(BaseExtractor):
    """
    Extracts daily OHLCV and delivery data from NSE Bhavcopy CSV files.

    Provides fields:
        date, open, high, low, close, volume, delivery_volume,
        delivery_percentage, turnover, trades_count, prev_close
    """

    def __init__(self):
        super().__init__(NSE_BHAVCOPY_CONFIG)
        self._delivery_config = NSE_DELIVERY_CONFIG

    def get_source_name(self) -> str:
        return "nse_bhavcopy"

    def get_provided_fields(self) -> List[str]:
        return [
            "date", "open", "high", "low", "close", "volume",
            "delivery_volume", "delivery_percentage", "turnover",
            "trades_count", "prev_close",
        ]

    async def extract(self, symbol: str, record: StockDataRecord) -> ExtractionRecord:
        """Extract latest daily data for a single symbol."""
        started_at = datetime.utcnow()
        fields_extracted = []
        fields_failed = []

        try:
            # Try today, then go back up to 5 days (weekends/holidays)
            for days_back in range(6):
                target_date = date.today() - timedelta(days=days_back)
                if target_date.weekday() >= 5:  # Skip weekends
                    continue

                data = await self._fetch_bhavcopy_for_date(target_date)
                if data is None:
                    continue

                row = data.get(symbol)
                if row is None:
                    continue

                # Set fields on record
                record.set_field("date", target_date.isoformat(), "nse_bhavcopy")
                fields_extracted.append("date")

                for field_name, csv_key in [
                    ("open", "OPEN"), ("high", "HIGH"), ("low", "LOW"),
                    ("close", "CLOSE"), ("prev_close", "PREVCLOSE"),
                    ("volume", "TOTTRDQTY"), ("turnover", "TOTTRDVAL"),
                    ("trades_count", "TOTALTRADES"),
                ]:
                    val = self._parse_field(row, csv_key, field_name)
                    if val is not None:
                        record.set_field(field_name, val, "nse_bhavcopy")
                        fields_extracted.append(field_name)
                    else:
                        fields_failed.append(field_name)

                # Try delivery data separately
                delivery_data = await self._fetch_delivery_for_date(target_date)
                if delivery_data and symbol in delivery_data:
                    drow = delivery_data[symbol]
                    for field_name, csv_key in [
                        ("delivery_volume", "DELIVERY_QTY"),
                        ("delivery_percentage", "DELIVERY_PER"),
                    ]:
                        val = self._parse_field(drow, csv_key, field_name)
                        if val is not None:
                            record.set_field(field_name, val, "nse_bhavcopy")
                            fields_extracted.append(field_name)

                break  # Found data, stop looking back

        except Exception as e:
            logger.error(f"Error extracting NSE Bhavcopy for {symbol}: {e}")
            return self._create_extraction_record(
                symbol, started_at, fields_extracted,
                self.get_provided_fields(), str(e)
            )

        fields_failed = [f for f in self.get_provided_fields() if f not in fields_extracted]
        return self._create_extraction_record(
            symbol, started_at, fields_extracted, fields_failed
        )

    async def extract_bulk(self, target_date: Optional[date] = None) -> Dict[str, Dict]:
        """
        Download and parse full Bhavcopy for a date, returning data for all symbols.

        Returns dict of {symbol: {field: value, ...}}
        """
        if target_date is None:
            target_date = date.today()

        for days_back in range(6):
            d = target_date - timedelta(days=days_back)
            if d.weekday() >= 5:
                continue
            data = await self._fetch_bhavcopy_for_date(d)
            if data is not None:
                return data

        return {}

    async def _fetch_bhavcopy_for_date(self, d: date) -> Optional[Dict[str, Dict]]:
        """
        Download and parse Bhavcopy CSV for a specific date.

        Returns: {symbol: {CSV_COLUMN: value, ...}} or None
        """
        month_str = MONTH_MAP[d.month]
        date_str = d.strftime("%d%b%Y").upper()
        url = (f"{self.config.base_url}/{d.year}/{month_str}/"
               f"cm{date_str}bhav.csv.zip")

        logger.info(f"Fetching Bhavcopy: {url}")

        # Download zip file to temp
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            success = await self._download_file(url, tmp_path)
            if not success:
                return None

            return self._parse_bhavcopy_zip(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _parse_bhavcopy_zip(self, zip_path: str) -> Optional[Dict[str, Dict]]:
        """Parse a Bhavcopy ZIP file and return stock data indexed by symbol."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                csv_files = [f for f in zf.namelist() if f.endswith('.csv')]
                if not csv_files:
                    return None

                with zf.open(csv_files[0]) as csv_file:
                    content = csv_file.read().decode('utf-8')

            result = {}
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                series = row.get("SERIES", "").strip()
                if series != "EQ":  # Only equity series
                    continue
                symbol = row.get("SYMBOL", "").strip()
                if symbol:
                    result[symbol] = {k.strip(): v.strip() for k, v in row.items()}

            logger.info(f"Parsed {len(result)} equity symbols from Bhavcopy")
            return result

        except (zipfile.BadZipFile, KeyError, UnicodeDecodeError) as e:
            logger.error(f"Error parsing Bhavcopy ZIP: {e}")
            return None

    async def _fetch_delivery_for_date(self, d: date) -> Optional[Dict[str, Dict]]:
        """Fetch delivery data for a specific date."""
        date_str = d.strftime("%d%m%Y")
        url = f"{self._delivery_config.base_url}/sec_bhavdata_full_{date_str}.csv"

        content = await self._fetch_url(url)
        if not content:
            return None

        try:
            result = {}
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                symbol = row.get(" SYMBOL", row.get("SYMBOL", "")).strip()
                if symbol:
                    result[symbol] = {k.strip(): v.strip() for k, v in row.items()}
            return result
        except Exception as e:
            logger.error(f"Error parsing delivery data: {e}")
            return None

    def _parse_field(self, row: Dict, csv_key: str, field_name: str) -> Optional[Any]:
        """Parse a single field from a CSV row."""
        val = row.get(csv_key, "").strip()
        if not val or val == "-":
            return None

        if field_name in ("volume", "delivery_volume", "trades_count"):
            return self.safe_int(val)
        elif field_name == "turnover":
            raw = self.safe_float(val)
            return round(raw / 1e7, 2) if raw is not None else None  # Convert to Cr
        else:
            return self.safe_float(val)

    async def fetch_historical_bhavcopy(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Dict]]:
        """
        Fetch Bhavcopy data for a date range.

        Returns list of daily data dicts.
        """
        all_data = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:  # Skip weekends
                data = await self._fetch_bhavcopy_for_date(current)
                if data:
                    all_data.append({"date": current.isoformat(), "data": data})
            current += timedelta(days=1)
        return all_data
