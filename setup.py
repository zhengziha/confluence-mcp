from setuptools import setup, find_packages

setup(
    name="confluence-mcp-server",
    version="0.1.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "mcp>=1.4.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "beautifulsoup4>=4.12.0",
        "markdown>=3.5.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "confluence-mcp-server=src.main:cli",
        ],
    },
)