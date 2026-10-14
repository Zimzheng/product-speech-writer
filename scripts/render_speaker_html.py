#!/usr/bin/env python3
"""Render reviewed talk JSON to an offline speaker file (Python stdlib only)."""
import argparse
import html
import json
import re
from pathlib import Path


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be a nonempty string')
    return value


def escaped(value):
    return html.escape(value, quote=True)


def highlighted(text, marks):
    require_text(text, 'block.text')
    spans = []
    for mark in marks:
        phrase = require_text(mark.get('text'), 'emphasis.text')
        if '\n\n' in phrase:
            raise ValueError('emphasis must stay inside one paragraph')
        kind = mark.get('kind')
        if kind not in ('key', 'boundary'):
            raise ValueError('emphasis.kind must be key or boundary')
        pos = text.find(phrase)
        if pos < 0:
            raise ValueError(f'emphasis text missing from its block: {phrase}')
        while pos >= 0:
            spans.append((pos, pos + len(phrase), kind))
            pos = text.find(phrase, pos + len(phrase))
    spans.sort()
    out, cursor = [], 0
    for start, end, kind in spans:
        if start < cursor:
            raise ValueError('overlapping emphasis spans')
        out += [escaped(text[cursor:start]), f'<strong class="emphasis {kind}">',
                escaped(text[start:end]), '</strong>']
        cursor = end
    out.append(escaped(text[cursor:]))
    return ''.join(out)


def paragraphs(text, marks=None):
    rendered = highlighted(text, marks or [])
    # Newlines are prose structure, never HTML or Markdown instructions.
    return ''.join('<p>' + p.replace('\n', '<br>') + '</p>'
                   for p in rendered.split('\n\n') if p.strip())


def clock(seconds):
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


def render(data):
    content_pool = []
    def content_paragraphs(text, marks=None):
        content_pool.append(paragraphs(text, marks))
        return f'<!--speaker-content-{len(content_pool)-1}-->'

    title = require_text(data.get('title'), 'title')
    language = data.get('language', 'zh-CN')
    if not isinstance(language, str) or not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', language):
        raise ValueError('language must be a valid language tag')
    english = not language.lower().startswith('zh')
    palette = data.get('palette', 'classic')
    if palette not in ('classic', 'monochrome'):
        raise ValueError('palette must be classic or monochrome')
    chapters = data.get('chapters')
    if not isinstance(chapters, list) or not chapters:
        raise ValueError('chapters must be a nonempty list')
    ids, sections, nav, elapsed = set(), [], [], 0
    for i, ch in enumerate(chapters):
        cid = require_text(ch.get('id'), 'chapter.id')
        if not re.fullmatch(r'[a-z][a-z0-9-]*', cid) or cid in ids:
            raise ValueError(f'invalid or duplicate chapter id: {cid}')
        ids.add(cid)
        heading = require_text(ch.get('title'), 'chapter.title')
        seconds = ch.get('seconds')
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds <= 0:
            raise ValueError('chapter.seconds must be a positive integer')
        timing = f'{clock(elapsed)}–{clock(elapsed + seconds)}'
        elapsed += seconds
        blocks = ch.get('blocks')
        if not isinstance(blocks, list) or not blocks:
            raise ValueError('chapter.blocks must be a nonempty list')
        sid = 'chapter-' + cid
        nav.append(f'<a href="#{sid}" data-target="{sid}"><span>{i+1:02d}</span>'
                   f'{escaped(heading)}<small>{timing}</small></a>')
        content = []
        for block in blocks:
            bid = require_text(block.get('id'), 'block.id')
            if not re.fullmatch(r'[a-z][a-z0-9-]*', bid) or bid in ids:
                raise ValueError(f'invalid or duplicate block id: {bid}')
            ids.add(bid)
            content.append(f'<div class="spoken" id="block-{bid}">')
            if block.get('label'):
                content.append('<h3>' + escaped(block['label']) + '</h3>')
            if block.get('cue'):
                content.append('<aside class="note cue"><b>现场提示 · 不朗读</b>'
                               + content_paragraphs(block['cue']) + '</aside>')
            content.append(content_paragraphs(block.get('text'), block.get('emphasis', [])))
            depth = block.get('depth', [])
            if not isinstance(depth, list):
                raise ValueError('block.depth must be an array')
            for j, extra in enumerate(depth):
                label = require_text(extra.get('label'), 'depth.label')
                content.append(f'<details class="deep" id="depth-{bid}-{j}">'
                               '<summary><span class="deep-tag">可选展开</span>'
                               + escaped(label) + '</summary><div class="spoken">'
                               '<div class="speech-label">接着上文讲 · 讲完继续下一段</div>'
                               + content_paragraphs(extra.get('text'), extra.get('emphasis', []))
                               + '</div></details>')
            content.append('</div>')
        transition = ''
        if ch.get('transition'):
            transition = '<div class="spoken bridge"><div class="speech-label">转场 · 直接口播</div>' + content_paragraphs(ch['transition']) + '</div>'
        metadata = ''
        if ch.get('claim'):
            metadata = '<div class="note metadata"><p>讲述目标：' + escaped(ch['claim']) + '</p></div>'
        sections.append(f'<section class="chapter" id="{sid}"><header>'
                        f'<div class="section-index">{i+1:02d} / {len(chapters):02d} · {timing}</div>'
                        '<h2>' + escaped(heading) + '</h2></header>' + metadata
                        + ''.join(content) + transition + '</section>')
    skill = Path(__file__).resolve().parents[1]
    css = (skill / 'assets/speaker.css').read_text()
    js = (skill / 'assets/speaker.js').read_text().replace('__BUDGET_SECONDS__', str(elapsed))
    if palette == 'monochrome':
        css += ':root{--speak:#233848}.dark{--speak:#e3edf2}.emphasis.key,.emphasis.boundary,.dark .emphasis.key,.dark .emphasis.boundary{color:var(--ink);background:transparent;box-shadow:none}.emphasis.key{border-bottom:3px solid currentColor}.emphasis.boundary{border:1px solid currentColor;border-bottom:2px solid currentColor}'
    if english:
        css = css.replace('font-family:"PingFang SC","Microsoft YaHei",sans-serif', 'font-family:system-ui,"Segoe UI",sans-serif')
    meta = escaped(data.get('subtitle', ''))
    legend = '<div class="legend"><b>直接口播</b><span><strong class="emphasis key">核心判断</strong></span><span><strong class="emphasis boundary">状态与门槛</strong></span><span>灰色路标、黄色提示：不朗读</span></div>'
    top = '<header class="top"><div class="brand">讲稿<small>主讲预算 ' + clock(elapsed) + ' · 展开与问答另计</small></div><div class="controls"><button id="smaller" aria-label="缩小口播字号">A−</button><span id="size">24px</span><button id="larger" aria-label="放大口播字号">A＋</button><button id="speech" aria-pressed="false">只看口播</button><button id="theme" aria-pressed="false">深色模式</button><button id="print">打印</button></div><div class="timer"><output id="time" aria-label="已讲时长">00:00</output><button id="start" aria-pressed="false">开始</button><button id="reset">归零</button></div></header>'
    page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + escaped(title) + '</title><style>' + css + '</style></head><body><div class="progress"></div>' + top + '<div class="layout"><aside class="sidebar"><h2>讲述顺序</h2><nav aria-label="章节导航">' + ''.join(nav) + '</nav><p>← → 切换章节<br>计时需点击开始</p></aside><main><article id="script" class="panel"><div class="intro"><h1>' + escaped(title) + '</h1><p>' + meta + '</p>' + legend + '</div>' + ''.join(sections) + '</article></main></div><nav class="bottom" aria-label="章节切换"><button id="prev">上一章</button><output id="position">1 / ' + str(len(chapters)) + '</output><button id="next">下一章</button></nav><script>' + js + '</script></body></html>'
    page = page.replace('<html lang="zh-CN">', '<html lang="' + escaped(language) + '">')
    if english:
        # Translate interface markup only; never translate or replace spoken text.
        ui = {
            '>讲稿<small>': '>Speaker notes<small>',
            '<small>主讲预算 ': '<small>Speaking budget ',
            ' · 展开与问答另计</small>': ' · Optional depth and Q&amp;A excluded</small>',
            '>现场提示 · 不朗读</b>': '>Delivery cue · Do not read aloud</b>',
            '>可选展开</span>': '>Optional depth</span>',
            '>接着上文讲 · 讲完继续下一段</div>': '>Continue from above, then resume the next block</div>',
            '>转场 · 直接口播</div>': '>Transition · Read aloud</div>',
            '<p>讲述目标：': '<p>Section goal: ',
            '>直接口播</b>': '>Read aloud</b>',
            '>核心判断</strong>': '>Key point</strong>',
            '>状态与门槛</strong>': '>Status or condition</strong>',
            '>灰色路标、黄色提示：不朗读</span>': '>Headings and cues are not spoken</span>',
            '>讲述顺序</h2>': '>Sections</h2>',
            '>← → 切换章节<br>计时需点击开始</p>': '>← → Navigate sections<br>Click Start to begin timing</p>',
            '>只看口播</button>': '>Speech only</button>',
            '>深色模式</button>': '>Dark mode</button>',
            '>打印</button>': '>Print</button>',
            '>开始</button>': '>Start</button>',
            '>归零</button>': '>Reset</button>',
            '>上一章</button>': '>Previous</button>',
            '>下一章</button>': '>Next</button>',
            'aria-label="缩小口播字号"': 'aria-label="Decrease speech font size"',
            'aria-label="放大口播字号"': 'aria-label="Increase speech font size"',
            'aria-label="已讲时长"': 'aria-label="Elapsed time"',
            'aria-label="章节导航"': 'aria-label="Section navigation"',
            'aria-label="章节切换"': 'aria-label="Navigate sections"',
        }
        for old, new in ui.items():
            page = page.replace(old, new)
        page = page.replace("running?'暂停':'开始'", "running?'Pause':'Start'")
    for i, content in enumerate(content_pool):
        page = page.replace(f'<!--speaker-content-{i}-->', content)
    return page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    result = render(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    print(args.output.resolve())


if __name__ == '__main__':
    main()
