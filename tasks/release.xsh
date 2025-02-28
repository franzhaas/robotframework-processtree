import os
import shutil

git checkout uv.lock
git_status = (str(!(git status)).split(os.linesep))
assert "nothing to commit, working tree clean" in git_status, f"please commit all changes before releasing (nothing to commit)"

version= input("which version to release?\n")

version = version.split(".")
assert len(version) == 3, "version must be in format x.y.z"
for item in version:
    assert item.isdigit(), "version must be in format x.y.z"

version = ".".join(version)

uv run --no-sync libdoc f"--version={version}" src/rf_processtree  docs/index.html
cp docs/index.html f"docs/robotframework_processtree-{version}.html"

shutil.rmtree("example_results/", ignore_errors=True)
uv run robot -L TRACE -d docs/example_results  atest/example/parent/

git add docs/index.html f"docs/robotframework_processtree-{version}.html"
git add docs/example_results/

input("please write an entry in the changelog at docs/release_notes.md and press enter to continue")
git commit -m f"release {version}"
git tag f"v{version}" -m "release {version} release process"
uv build
uv publish
git push --tags
