# path_walker

一个支持捕获组的路径匹配库。用法类似 glob，但捕获组标记的部分会被**提取并返回**，而不是仅用于过滤。默认使用 `{}` 作为捕获组括号，也可通过 `bracket="[]"` 切换为 `[]`。

## 安装

```bash
pip install -e .
```

## 快速开始

```python
from path_walker import walk, walk_first
```

---

## 模式语法

| 语法 | 含义 |
|------|------|
| `*` | 匹配单个路径段（不跨越 `/`） |
| `**` | 匹配零或多个路径段（可跨越 `/`） |
| `?` | 匹配单个字符（不跨越 `/`） |
| `{P}` | **捕获组**（默认）：匹配模式 `P`，将匹配到的内容作为结果返回 |
| `[P]` | **捕获组**（`bracket="[]"` 时）：与 `{P}` 语义相同 |

捕获组内部同样支持 `*`、`**`、`?` 以及字面量，且可以包含 `/`（跨目录捕获）。

同一 pattern 中只使用一种括号作为捕获组，另一种视为字面量。当路径中包含 `{}`
字面量字符时，可切换为 `bracket="[]"`，反之亦然。

---

## 返回值规则

捕获组数量决定返回值的形状：

| 捕获组数量 | 返回类型 | 说明 |
|-----------|----------|------|
| 0 | `list[str]` | 所有匹配的完整路径 |
| 1 | `list[str]` | 每个匹配的捕获内容 |
| 2+ | `list[list[str]]` | 每个匹配的所有捕获内容（2D） |

---

## 使用示例

### 查找包含指定文件的目录

```python
# 找出所有直接包含 image.jpg 的目录名
walk('/photos/{*}/image.jpg')
# -> ['2023', '2024']
```

### 多级捕获

```python
# 找出 data/ 下所有形如 */bbb 的子路径
walk('./data/{*/bbb}')
# -> ['a/bbb', 'b/bbb']
```

`{*/bbb}` 是一个跨两级目录的捕获组，匹配 `任意名称/bbb` 并将整段作为结果返回。

### 2D 结果（多个捕获组）

```python
# 同时捕获 子目录名 和 文件名（不含扩展名）
walk('/photos/{*}/{*}.jpg')
# -> [['2023', 'holiday'], ['2023', 'beach'], ['2024', 'sunset']]
```

### 内联捕获组

捕获组可以嵌在文件名中间，而不必占据整个路径段：

```python
# {c} 只匹配字面量 'c'，文件必须叫 abc.png
walk('/{*}/ab{c}.png')
# -> [['photos', 'c'], ['raw', 'c']]

# {z.png} 匹配字面量 'z.png'（. 被转义）
walk('/{*}/ababa/{z.png}')
# -> [['art', 'z.png'], ['raw', 'z.png']]
```

### 无捕获组（纯过滤）

```python
# 返回完整路径列表
walk('./docs/*.pdf')
# -> ['/abs/path/to/docs/report.pdf']
```

### `**` 跨多级搜索

```python
# 找出任意深度下所有 .jpg 文件，捕获文件名（不含扩展名）
walk('./root/**/{*}.jpg')
# -> ['holiday', 'beach', 'sunset', 'image']
```

### `walk_first`

```python
# 返回第一个匹配，没有则返回 None
walk_first('./docs/{*}.pdf')
# -> 'report'
```

---

## API

### `walk(pattern, *, root=None, bracket="{}")`

遍历文件系统，返回所有匹配 `pattern` 的结果。

**参数**

- `pattern` — 路径模式，支持绝对路径和相对路径。
- `root` — 可选，覆盖遍历起始目录。默认从 `pattern` 的字面量前缀自动推断。
- `bracket` — 可选，指定捕获组括号。`"{}"` (默认) 或 `"[]"`。

**返回值** — 见[返回值规则](#返回值规则)。

---

### `walk_first(pattern, *, root=None, bracket="{}")`

返回第一个匹配结果，没有匹配则返回 `None`。

---

## 捕获组详解

### 捕获组内的 `*` 与 `**`

以下以默认的 `{}` 为例（`[]` 模式等价）：

| 写法 | 匹配 |
|------|------|
| `{*}` | 一个路径段（不含 `/`） |
| `{**}` | 一或多个字符（含 `/`，可跨多级） |
| `{*/sub}` | 任意一级目录 + `/sub` |
| `{**.log}` | 任意路径结尾为 `.log` |

### 捕获组内的字面量

捕获组内部所有非通配符字符均视为字面量（包括 `.`）：

```
{z.png}   匹配且只匹配文件名 z.png
{c}       匹配且只匹配字符 c
{ab{c}d}  不支持嵌套 {}
```

### 使用 `[]` 捕获组

当路径中包含 `{` 或 `}` 字面量字符时，可切换为 `[]` 模式：

```python
# 目录名本身包含花括号，如 {data}/
walk('{data}/[*].csv', bracket="[]")
# -> ['report']

# 等价于默认模式的 data/{*}.csv（若路径无花括号）
walk('data/[*].csv', bracket="[]")
```

使用 `[]` 模式时，`{}` 被视为普通字面量字符。

---

## Windows 路径说明

path_walker 在内部统一使用 `/` 作为路径分隔符。

**输入 pattern**：`/` 和 `\\` 均可，库会自动转换。

```python
walk('C:/Users/Kevin/{*}/image.jpg')      # ✓
walk('C:\\Users\\Kevin\\{*}\\image.jpg')  # ✓ 等价
```

**输出结果**：无论运行在何种平台，返回值始终使用 `/`。

```python
# 1 个捕获组 -> 捕获内容本身，不含分隔符
walk('C:/Users/{*}/image.jpg')
# -> ['Kevin']

# 0 个捕获组 -> 完整路径，用 / 分隔（非 \）
walk('C:/Users/Kevin/docs/*.pdf')
# -> ['C:/Users/Kevin/docs/report.pdf']
```

---

## 项目结构

```
path_walker/
  path_walker/
    __init__.py   # 导出 walk, walk_first
    pattern.py    # 模式解析与正则转换
    walker.py     # 文件系统遍历逻辑
  tests/
    test_pattern.py
    test_walker.py
  pyproject.toml
```

---

## 运行测试

```bash
pip install pytest
pytest tests/
```

---

## 许可证

[GNU Lesser General Public License v2.1](LICENSE)

- 闭源项目可以 `import` 并使用本库 ✅
- 修改本库代码必须以 LGPL-2.1 开源 ✅
- 必须保留原作者署名 ✅
