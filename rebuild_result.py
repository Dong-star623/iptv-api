# -*- coding: utf-8 -*-
"""
从 result.log 重建 user_result.txt
解决 iptv-api 结果聚合 bug 导致央视分类为空的问题
"""
import sys
import io
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 分类规则(频道名前缀 → 分类)
def get_category(name):
    if name.startswith('CCTV') or name.startswith('CETV'):
        return '📺央视频道'
    # 卫视判断
    if name.endswith('卫视') or name in ['广东卫视', '香港卫视']:
        return '📡卫视频道'
    # 广东本地
    if any(x in name for x in ['广东', '广州', '深圳', '佛山', '江门', '汕头', '茂名', '大湾区']):
        return '☘️广东频道'
    # 湖北本地
    if any(x in name for x in ['湖北', '武汉']):
        return '🌸湖北频道'
    # 少儿
    if any(x in name for x in ['卡通', '少儿', '动漫', '宝贝']):
        return '👶少儿/卡通频道'
    # 央视专业(风云/剧场等)
    if any(x in name for x in ['风云', '剧场', '地理', '足球', '高尔夫', '武术', '影像', '时尚', '台球']):
        return '🎬央视专业/付费频道'
    # 默认归到其他/卫视
    return '📡卫视频道'

# 解析 result.log
entries = []  # [(频道, 接口, 速率, 分辨率, 延迟)]
with open('output/log/result.log', 'r', encoding='utf-8') as f:
    for line in f:
        m = re.search(r'名称: (.+?), 接口: (.+?), 来源: .+?, 协议类型: (\w+).*?延迟: (\d+) ms, 速率: ([\d.]+) M/s, 分辨率: (\S+)', line)
        if m:
            name = m.group(1).strip()
            url = m.group(2).strip()
            proto = m.group(3)
            delay = int(m.group(4))
            speed = float(m.group(5))
            resolution = m.group(6)
            entries.append((name, url, proto, delay, speed, resolution))

print(f"解析到 {len(entries)} 个有效接口")

# 按分类组织,每个频道按速率排序,最多保留 5 个
from collections import defaultdict
cat_channels = defaultdict(lambda: defaultdict(list))
for name, url, proto, delay, speed, resolution in entries:
    cat = get_category(name)
    cat_channels[cat][name].append((url, proto, delay, speed, resolution))

# 排序:每个频道的接口按速率降序,最多 urls_limit 个
for cat in cat_channels:
    for ch in cat_channels[cat]:
        cat_channels[cat][ch].sort(key=lambda x: -x[3])
        cat_channels[cat][ch] = cat_channels[cat][ch][:5]

# 生成结果文件
lines = []
# 更新时间分类
import datetime
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# 找一个最快的接口作为更新时间的展示
fastest = max(entries, key=lambda x: x[4]) if entries else None
lines.append('🕘️更新时间,#genre#')
if fastest:
    lines.append(f'{now},{fastest[1]}$订阅源')
lines.append('')

# 各分类
category_order = ['📺央视频道', '🎬央视专业/付费频道', '📡卫视频道', '👶少儿/卡通频道', '☘️广东频道', '🌸湖北频道']
for cat in category_order:
    if cat not in cat_channels:
        continue
    lines.append(f'{cat},#genre#')
    for ch_name in sorted(cat_channels[cat].keys()):
        for url, proto, delay, speed, resolution in cat_channels[cat][ch_name]:
            lines.append(f'{ch_name},{url}$订阅源')
    lines.append('')

content = '\n'.join(lines)

with open('output/user_result.txt', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n重建完成!写入 {len(entries)} 个接口到 output/user_result.txt")
print(f"\n分类统计:")
for cat in category_order:
    if cat in cat_channels:
        ch_count = len(cat_channels[cat])
        if_count = sum(len(v) for v in cat_channels[cat].values())
        print(f"  {cat:<22} 频道:{ch_count:<4} 接口:{if_count}")
