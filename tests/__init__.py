from pathlib import Path

TEST_OUTPUT_DIR = Path(__file__).parent.parent.joinpath("tmp")
TEST_OUTPUT_DIR.mkdir(exist_ok=True)
