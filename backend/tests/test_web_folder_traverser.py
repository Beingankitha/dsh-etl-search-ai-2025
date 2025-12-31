import pytest
from aioresponses import aioresponses

from src.infrastructure.http_client import AsyncHTTPClient
from src.services.web_folder_traverser import WebFolderTraverser


SAMPLE_HTML = """
<html>
<body>
<h1>Index of /data/</h1>
<a href="file1.pdf">file1.pdf</a><br>
<a href="file2.txt">file2.txt</a><br>
<a href="subfolder/">subfolder/</a><br>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_discover_files_in_folder():
    """Test file discovery from HTML directory listing."""
    with aioresponses() as mocked:
        url = "https://example.com/data/"
        mocked.get(url, body=SAMPLE_HTML)

        async with AsyncHTTPClient() as client:
            traverser = WebFolderTraverser(client)
            files = await traverser.discover_files(url, recursive=False)

            # Should find 2 files (not recurse to subfolder)
            assert len(files) >= 2
            assert any("file1.pdf" in f for f in files)
            assert any("file2.txt" in f for f in files)


@pytest.mark.asyncio
async def test_traverser_identifies_file_types():
    """Test that traverser correctly identifies files vs folders."""
    traverser = WebFolderTraverser(None)

    assert traverser._is_file("https://example.com/report.pdf")
    assert traverser._is_file("https://example.com/data.zip")
    assert not traverser._is_file("https://example.com/folder/")
    assert traverser._is_folder("https://example.com/data/")
    assert not traverser._is_folder("https://example.com/file.pdf")