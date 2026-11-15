import pytest

from flarefuzz_api.models import DatasetMetadata
from flarefuzz_api.parsers import (
    AmbiguousFileParserError,
    CSVParser,
    ParserContext,
    ParserRegistry,
    UnsupportedFileTypeError,
)


def _context(filename, media_type):
    return ParserContext(
        filename=filename,
        media_type=media_type,
        metadata=DatasetMetadata(),
    )


def test_registry_dispatches_csv_and_returns_normalized_values():
    registry = ParserRegistry((CSVParser(),))
    result = registry.parse(
        b"Flame diameter (mm)\n12\n",
        _context("measurements.csv", "text/csv"),
    )
    assert result.si_values == [{"flame_diameter#1": pytest.approx(0.012)}]


@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        ("measurements.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("record.pdf", "application/pdf"),
        ("record.mp4", "video/mp4"),
        ("record.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ],
)
def test_mvp_registry_rejects_unregistered_formats(filename, media_type):
    with pytest.raises(UnsupportedFileTypeError):
        ParserRegistry((CSVParser(),)).parse(b"binary", _context(filename, media_type))


def test_registry_rejects_ambiguous_parser_registration():
    with pytest.raises(AmbiguousFileParserError):
        ParserRegistry((CSVParser(), CSVParser())).parse(
            b"Flame diameter (mm)\n12\n",
            _context("measurements.csv", "text/csv"),
        )
