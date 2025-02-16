from setuptools import setup, find_namespace_packages

setup(
    name="trader-tony",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_namespace_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "solana==0.30.2",
        "solders==0.18.1",
        "python-dotenv==1.0.0",
        "asyncio>=3.4.3",
        "websockets>=11.0.3",
        "aiohttp>=3.8.0",
        "dataclasses>=0.6",
        "typing-extensions>=4.2.0",
        "mnemonic>=0.20"
    ],
    description="Solana trading bot with Raydium DEX integration",
    author="Tony",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
