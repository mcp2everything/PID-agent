from setuptools import setup, find_packages

setup(
    name="pid-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "streamlit>=1.0.0",
        "pandas>=1.3.0",
        "plotly>=5.0.0",
        "python-dotenv>=0.19.0",
        "langchain>=0.1.0",
        "langchain-deepseek-official>=0.1.0",
        "pyserial>=3.5",
        "pydantic>=2.7.0",
        "pydantic-settings>=2.0.0",
        "requests>=2.26.0",
    ],
)
