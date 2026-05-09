# Python 3.14 安装依赖问题解决方案

## 问题说明
Python 3.14 太新了，某些包（如pydantic-core）可能没有预编译的wheel包，需要从源码编译，而编译需要Rust工具链。

## 解决方案

### 方案1：使用预编译包（推荐）

已经更新了 `requirements.txt`，移除了版本限制。尝试安装：

```bash
pip3 install -r requirements.txt
```

如果pydantic-core仍然需要编译，可以尝试：

```bash
# 先尝试安装pydantic-core的预编译版本
pip3 install --upgrade pip3
pip3 install pydantic-core --only-binary :all:

# 如果上面成功，再安装其他依赖
pip3 install -r requirements.txt
```

### 方案2：使用国内镜像（可能更快）

```bash
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 方案3：手动安装Rust（如果方案1失败）

如果确实需要编译，可以安装Rust：

```bash
# 安装Rust（这会需要一些时间）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 重新加载环境
source ~/.cargo/env

# 然后再安装依赖
pip3 install -r requirements.txt
```

### 方案4：使用Python 3.11或3.12（最稳定）

如果上述方案都有问题，建议使用Python 3.11或3.12，这些版本有更多的预编译包：

```bash
# 使用Homebrew安装Python 3.12
brew install python@3.12

# 创建新的虚拟环境
cd backend
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip3 install -r requirements.txt
```

## 当前状态

已更新 `requirements.txt` 文件，移除了具体版本号，让pip3自动选择兼容的版本。

先试试方案1，如果还有问题再尝试其他方案。

