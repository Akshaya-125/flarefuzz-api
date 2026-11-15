from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol

import pandas as pd
import pint

from flarefuzz_api.models import DatasetMetadata, NormalizedCSVResponse
from flarefuzz_api.normalizer import inventory_csv, normalized_csv_response


@dataclass(frozen=True)
class ParserContext:
    filename: str | None
    media_type: str | None
    metadata: DatasetMetadata
    options: Mapping[str, object] = field(default_factory=dict)


class FileParser(Protocol):
    """Strategy contract for a format-specific file parser."""

    def supports(self, filename: str | None, media_type: str | None) -> bool: ...

    def parse(self, content: bytes, context: ParserContext) -> NormalizedCSVResponse: ...


class UnsupportedFileTypeError(LookupError):
    pass


class AmbiguousFileParserError(RuntimeError):
    pass


class CSVParser:
    _CSV_MEDIA_TYPES = {"text/csv", "application/csv"}
    _GENERIC_MEDIA_TYPES = {"application/octet-stream", "binary/octet-stream", "text/plain"}

    def supports(self, filename: str | None, media_type: str | None) -> bool:
        suffix = Path(filename).suffix.lower() if filename else ""
        normalized_type = (media_type or "").split(";", 1)[0].strip().lower()
        if suffix and suffix != ".csv":
            return False
        if normalized_type and normalized_type not in self._CSV_MEDIA_TYPES | self._GENERIC_MEDIA_TYPES:
            return False
        return suffix == ".csv" or normalized_type in self._CSV_MEDIA_TYPES

    def parse(self, content: bytes, context: ParserContext) -> NormalizedCSVResponse:
        unknown_options = set(context.options) - {"header_rows"}
        if unknown_options:
            raise ValueError(f"Unsupported CSV parser options: {sorted(unknown_options)}")
        header_rows = context.options.get("header_rows")
        if header_rows is not None and (
            isinstance(header_rows, bool) or not isinstance(header_rows, int)
        ):
            raise ValueError("header_rows must be an integer.")
        inventory, data = inventory_csv(
            content,
            metadata=context.metadata,
            header_rows=header_rows,
        )
        return normalized_csv_response(inventory, data)


class ParserRegistry:
    def __init__(self, parsers: tuple[FileParser, ...] = ()):
        self._parsers = list(parsers)

    def register(self, parser: FileParser) -> None:
        self._parsers.append(parser)

    def parse(self, content: bytes, context: ParserContext) -> NormalizedCSVResponse:
        matches = [
            parser
            for parser in self._parsers
            if parser.supports(context.filename, context.media_type)
        ]
        if not matches:
            raise UnsupportedFileTypeError(
                f"No parser is registered for file {context.filename or context.media_type!r}."
            )
        if len(matches) > 1:
            raise AmbiguousFileParserError(
                f"Multiple parsers match file {context.filename or context.media_type!r}."
            )
        try:
            return matches[0].parse(content, context)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, pint.errors.PintError) as exc:
            raise ValueError(f"Could not parse CSV input: {exc}") from exc


DEFAULT_PARSER_REGISTRY = ParserRegistry((CSVParser(),))
