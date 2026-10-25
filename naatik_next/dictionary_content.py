"""Bounded Yomitan v3 text trees; HTML is generated, never taken from the ZIP."""
from .i18n import t
from html import escape
import json
from .storage import UserError

TAGS = {'br', 'ruby', 'rt', 'rp', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th',
        'span', 'div', 'ol', 'ul', 'li', 'details', 'summary', 'a'}
STYLES = {'fontStyle', 'fontWeight', 'fontSize', 'color', 'background', 'backgroundColor',
          'textDecorationLine', 'textDecorationStyle', 'textDecorationColor', 'borderColor',
          'borderStyle', 'borderRadius', 'borderWidth', 'clipPath', 'verticalAlign', 'textAlign',
          'textEmphasis', 'textShadow', 'margin', 'marginTop', 'marginLeft', 'marginRight',
          'marginBottom', 'padding', 'paddingTop', 'paddingLeft', 'paddingRight', 'paddingBottom',
          'wordBreak', 'whiteSpace', 'cursor', 'listStyleType'}


def validate_meanings(meanings):
    budget = [0]
    def tree(node, depth=0):
        budget[0] += 1
        if depth > 32 or budget[0] > 20000:
            raise UserError(t('Contenido enriquecido excesivo: máximo profundidad 32 y 20 000 nodos por entrada.'))
        if isinstance(node, str):
            return
        if isinstance(node, list):
            for child in node:
                tree(child, depth + 1)
            return
        if not isinstance(node, dict) or not isinstance(node.get('tag'), str) or node['tag'] not in TAGS:
            raise UserError(t('Elemento enriquecido no compatible; no se admiten scripts, imágenes ni recursos.'))
        tag = node['tag']
        allowed = {'tag', 'content', 'data', 'lang'}
        if tag in {'span', 'div', 'ol', 'ul', 'li', 'details', 'summary', 'td', 'th'}:
            allowed.add('style')
        if tag in {'span', 'div', 'ol', 'ul', 'li', 'details', 'summary'}:
            allowed.update({'title', 'open'})
        if tag in {'td', 'th'}:
            allowed.update({'colSpan', 'rowSpan'})
        if tag == 'a':
            allowed.add('href')
            href = node.get('href')
            if not isinstance(href, str) or not href.startswith(('?', 'http:', 'https:')):
                raise UserError(t('Referencia de diccionario inválida; solo se conserva como texto.'))
        if set(node) - allowed or (tag == 'br' and set(node) - {'tag', 'data'}):
            raise UserError((t('Atributo enriquecido no compatible en ') + f'{tag}' + '.'))
        for key in ('lang', 'title'):
            if key in node and not isinstance(node[key], str):
                raise UserError((f'{key}' + t(' debe ser texto.')))
        if 'open' in node and type(node['open']) is not bool:
            raise UserError(t('open debe ser booleano.'))
        for key in ('colSpan', 'rowSpan'):
            if key in node and (type(node[key]) is not int or not 1 <= node[key] <= 100):
                raise UserError(t('Tabla demasiado grande o con extensión inválida (1–100).'))
        data = node.get('data', {})
        if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
            raise UserError(t('Atributos data inválidos.'))
        style = node.get('style', {})
        if not isinstance(style, dict) or set(style) - STYLES:
            raise UserError(t('Estilo enriquecido no compatible.'))
        for key, value in style.items():
            if isinstance(value, str):
                continue
            if key in {'marginTop', 'marginLeft', 'marginRight', 'marginBottom'} and type(value) in (int, float):
                continue
            if key == 'textDecorationLine' and isinstance(value, list) and all(isinstance(v, str) for v in value):
                continue
            raise UserError(t('Valor de estilo inválido.'))
        if 'content' in node:
            tree(node['content'], depth + 1)
    if not isinstance(meanings, list) or not meanings:
        raise UserError(t('Se requiere una lista de significados.'))
    if len(json.dumps(meanings, ensure_ascii=False)) > 2_000_000:
        raise UserError(t('Definición superior a 2 millones de caracteres.'))
    for item in meanings:
        if isinstance(item, str):
            tree(item)
        elif isinstance(item, dict) and item.get('type') == 'text' and set(item) == {'type', 'text'} and isinstance(item['text'], str):
            tree(item['text'])
        elif isinstance(item, dict) and item.get('type') == 'structured-content' and set(item) == {'type', 'content'}:
            tree(item['content'])
        else:
            raise UserError(t('Definición enriquecida no compatible: solo text y structured-content; no medios ni desinflexión.'))


def render_tree(node):
    if isinstance(node, str):
        return escape(node).replace('\n', '<br>')
    if isinstance(node, list):
        return ''.join(render_tree(x) for x in node)
    tag = node['tag']
    content = render_tree(node.get('content', ''))
    # No href, URLs, raw CSS, or archive attributes enter the QTextDocument.
    if tag == 'a':
        return content + ' <small>(referencia: ' + escape(node['href']) + ')</small>'
    if tag == 'br':
        return '<br>'
    if tag in {'ruby', 'rp', 'details', 'summary'}:
        tag = 'span' if tag in {'ruby', 'rp'} else 'div'
    elif tag == 'rt':
        return '(' + content + ')'
    attrs = ''
    if tag == 'table':
        attrs = ' border="1" cellspacing="0" cellpadding="4"'
    if tag in {'td', 'th'}:
        for key, html_key in [('colSpan', 'colspan'), ('rowSpan', 'rowspan')]:
            if key in node:
                attrs += f' {html_key}="{node[key]}"'
    style = node.get('style', {})
    if style.get('fontWeight') == 'bold':
        content = '<b>' + content + '</b>'
    if style.get('fontStyle') == 'italic':
        content = '<i>' + content + '</i>'
    if style.get('textAlign') in {'left', 'right', 'center', 'justify'} and tag in {'td', 'th', 'div'}:
        attrs += ' align="' + style['textAlign'] + '"'
    if node.get('data', {}).get('content') == 'examples':
        content = '<li><b>Ejemplos</b></li>' + content if tag in {'ul', 'ol'} else '<b>Ejemplos</b>' + content
    caption = '<small>[' + escape(node['lang']) + ']</small> ' if node.get('lang') else ''
    if tag not in {'ul', 'ol', 'table', 'tr', 'thead', 'tbody', 'tfoot'}:
        content = caption + content
        caption = ''
    return caption + f'<{tag}{attrs}>' + content + f'</{tag}>'


def origin(row):
    revision = ' · ' + row['revision'] if row.get('revision') else ''
    return t('<p><b>Diccionario:</b> ') + escape(row['title'] + revision) + '</p>'


def render_pitch(row):
    from .dictionary_archive import validate_pitch
    pitches = json.loads(row['pitches'])
    validate_pitch({'reading': row['reading'], 'pitches': pitches})
    lines = []
    for pitch in pitches:
        position = pitch['position']
        if isinstance(position, str):
            description = t('Patrón explícito: ') + position + ' (H = alto, L = bajo)'
        elif position == 0:
            description = t('[0] Sin caída (heiban)')
        else:
            description = ('[' + f'{position}' + t('] Caída después de la mora ') + f'{position}')
        detail = []
        for key, label in [('tags',t('Etiquetas')),('nasal','Nasal'),('devoice','Ensordecimiento')]:
            if key in pitch:
                detail.append(label + ': ' + json.dumps(pitch[key],ensure_ascii=False))
        lines.append('<li>' + escape(description) + (' — ' + escape('; '.join(detail)) if detail else '') + '</li>')
    return '<ul>' + (''.join(lines) or t('<li>Sin patrones de acento en este registro.</li>')) + '</ul>' + origin(row)


def render_results(results):
    groups = {kind: [] for kind in ('term','grammar','kanji','pitch')}
    for row in results:
        kind = row.get('kind','term')
        if kind not in groups:
            raise UserError(t('Tipo de resultado de diccionario no compatible.'))
        heading = '<h3>' + escape(row['expression'])
        if row.get('reading'):
            heading += ' 【' + escape(row['reading']) + '】'
        heading += '</h3>'
        if kind == 'pitch':
            groups[kind].append(heading + render_pitch(row))
            continue
        if kind == 'kanji':
            from .dictionary_archive import validate_kanji
            meanings, attributes = json.loads(row['meanings']),json.loads(row['attributes'])
            validate_kanji([row['expression'],row['onyomi'],row['kunyomi'],row['tags'],meanings,attributes])
            body = '<p><b>On:</b> ' + escape(row['onyomi']) + '<br><b>Kun:</b> ' + escape(row['kunyomi']) + '</p>'
            body += '<ul>' + ''.join('<li>' + escape(m) + '</li>' for m in meanings) + '</ul>'
            body += '<p>Etiquetas: ' + escape(row['tags']) + '</p><table border="1" cellpadding="3">'
            body += ''.join('<tr><th>'+escape(k)+'</th><td>'+escape(v)+'</td></tr>' for k,v in attributes.items()) + '</table>'
            groups[kind].append(heading + origin(row) + body)
            continue
        meanings = json.loads(row['meanings'])
        validate_meanings(meanings)
        body = []
        for item in meanings:
            node = item if isinstance(item,str) else item.get('text',item.get('content'))
            body.append('<div>' + render_tree(node) + '</div>')
        tags = ''
        if row.get('source_row'):
            source = json.loads(row['source_row'])
            tags = '<p>Etiquetas: ' + escape(' '.join(x for x in [source[2],source[7]] if x)) + '</p>'
        matched = ''
        for accent in row.get('accents',[]):
            # Defense in depth: never associate by expression alone.
            if (accent['expression'],accent['reading']) == (row['expression'],row['reading']):
                matched += t('<p><b>Acento para esta expresión y lectura:</b></p>') + render_pitch(accent)
        groups[kind].append(heading + origin(row) + tags + ''.join(body) + matched)
    captions = {'term':t('Términos / bilingües'), 'grammar':t('Gramática — consulta exacta, sin análisis de frases'),
                'kanji':'Kanji — significados, lecturas y atributos', 'pitch':t('Acento tonal — por expresión y lectura')}
    return ''.join('<h2>'+caption+'</h2>'+'<hr>'.join(groups[kind]) for kind,caption in captions.items() if groups[kind])
