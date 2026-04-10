import streamlit as st
import json
import re
import time
import base64
import requests

GITHUB_REPO  = 'kotaromiura/drug-cards'
DRUGS_FILE   = 'drugs.json'
HTML_FILE    = 'casa_druginfo.html'

CATEGORIES = ['循環器', '糖尿病', 'アレルギー', '小児', '風邪', '消化器', 'その他',
              '感染症', '呼吸器', '解熱鎮痛', '皮膚科', '漢方', '睡眠', '外用薬']

CAT_STYLES = {
    '循環器':    {'bg': 'rgba(0,113,227,0.1)',   'color': '#0055b3', 'dot': '#0055b3'},
    '糖尿病':    {'bg': 'rgba(52,199,89,0.1)',   'color': '#1a7f37', 'dot': '#1a7f37'},
    'アレルギー':{'bg': 'rgba(255,149,0,0.1)',   'color': '#b85c00', 'dot': '#b85c00'},
    '小児':      {'bg': 'rgba(175,82,222,0.1)',  'color': '#7b2fbe', 'dot': '#7b2fbe'},
    '風邪':      {'bg': 'rgba(90,200,250,0.15)', 'color': '#0077a8', 'dot': '#0077a8'},
    '消化器':    {'bg': 'rgba(100,200,100,0.1)', 'color': '#1a6b1a', 'dot': '#1a6b1a'},
    '感染症':    {'bg': 'rgba(255,59,48,0.1)',   'color': '#c0392b', 'dot': '#c0392b'},
    '呼吸器':    {'bg': 'rgba(100,180,255,0.15)','color': '#0055b3', 'dot': '#005ab5'},
    '解熱鎮痛':  {'bg': 'rgba(255,200,0,0.15)',  'color': '#8a6000', 'dot': '#8a6000'},
    '皮膚科':    {'bg': 'rgba(255,150,150,0.15)','color': '#a03030', 'dot': '#a03030'},
    '漢方':      {'bg': 'rgba(180,140,80,0.15)', 'color': '#6b4e00', 'dot': '#6b4e00'},
    '睡眠':      {'bg': 'rgba(130,100,220,0.15)','color': '#4a2fa0', 'dot': '#4a2fa0'},
    '外用薬':    {'bg': 'rgba(200,200,200,0.2)', 'color': '#444',    'dot': '#888'},
    'その他':    {'bg': 'rgba(0,0,0,0.06)',      'color': '#555',    'dot': '#aaa'},
}

st.set_page_config(page_title='お薬管理 — カーサファミリークリニック', layout='wide')

# ===== パスワード認証 =====
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title('🔐 カーサファミリークリニック')
    st.subheader('お薬管理システム')
    st.write('')
    pw = st.text_input('パスワード', type='password', placeholder='パスワードを入力')
    if st.button('ログイン', type='primary'):
        correct = st.secrets.get('PASSWORD', 'casaFC2024')
        if pw == correct:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error('パスワードが違います')
    st.stop()

# ===== GitHub API =====
def gh_token():
    return st.secrets.get('GITHUB_TOKEN', '')

def gh_headers():
    return {'Authorization': f'token {gh_token()}', 'Content-Type': 'application/json'}

def gh_get_file(path):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    r = requests.get(url, headers=gh_headers())
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    return content, data['sha']

def gh_put_file(path, content_str, sha, message):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    data = {
        'message': message,
        'content': base64.b64encode(content_str.encode('utf-8')).decode('utf-8'),
        'sha': sha
    }
    r = requests.put(url, headers=gh_headers(), json=data)
    r.raise_for_status()

def load_drugs():
    try:
        content, sha = gh_get_file(DRUGS_FILE)
        st.session_state['drugs_sha'] = sha
        return json.loads(content)
    except Exception as e:
        st.error(f'データの読み込みに失敗しました: {e}')
        return []

def save_drugs(drugs):
    drugs_str = json.dumps(drugs, ensure_ascii=False, indent=2)
    sha = st.session_state.get('drugs_sha', '')

    # drugs.json を更新
    gh_put_file(DRUGS_FILE, drugs_str, sha, 'Update drugs.json via admin')

    # HTML に埋め込みデータを更新
    try:
        html_content, html_sha = gh_get_file(HTML_FILE)
        drugs_json = json.dumps(drugs, ensure_ascii=False)
        inline = f'  // ===== データ直接埋め込み =====\n  DRUGS = {drugs_json};\n  renderList();'
        html_new = re.sub(
            r'  // ===== データ直接埋め込み =====\n  DRUGS = .*?;\n  renderList\(\);',
            inline,
            html_content,
            flags=re.DOTALL
        )
        gh_put_file(HTML_FILE, html_new, html_sha, 'Update HTML drug data via admin')
    except Exception as e:
        st.warning(f'HTMLの自動更新に失敗しました（drugs.jsonは保存済み）: {e}')

    # SHA を更新
    try:
        _, new_sha = gh_get_file(DRUGS_FILE)
        st.session_state['drugs_sha'] = new_sha
    except:
        pass

def make_id():
    return 'drug_' + str(int(time.time() * 1000))

def get_categories(d):
    cats = d.get('categories', d.get('category', ''))
    if isinstance(cats, list):
        return cats
    return [cats] if cats else []

# ===== 初期化 =====
if 'drugs' not in st.session_state:
    st.session_state.drugs = load_drugs()
if 'mode' not in st.session_state:
    st.session_state.mode = 'list'
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

def reload():
    st.session_state.drugs = load_drugs()

# ===== ヘッダー =====
st.title('💊 お薬管理')
st.caption('カーサファミリークリニック — 院内処方お薬ガイド管理画面')

col_logout, _ = st.columns([1, 9])
with col_logout:
    if st.button('ログアウト'):
        st.session_state.authenticated = False
        st.rerun()

st.divider()

col_add, col_reload, _ = st.columns([1, 1, 6])
with col_add:
    if st.button('＋ 新規追加', type='primary'):
        st.session_state.mode = 'add'
        st.session_state.edit_id = None
with col_reload:
    if st.button('🔄 再読込'):
        reload()
        st.session_state.mode = 'list'

st.divider()

drugs = st.session_state.drugs

# ===================================================================
# 薬フォーム（追加 / 編集）
# ===================================================================
if st.session_state.mode in ('add', 'edit'):
    is_edit = st.session_state.mode == 'edit'
    target = next((d for d in drugs if d['id'] == st.session_state.edit_id), None) if is_edit else {}

    st.subheader('✏️ 薬の編集' if is_edit else '＋ 新規薬の追加')

    current_cats = get_categories(target) if target else []
    default_cats = [c for c in current_cats if c in CATEGORIES]

    with st.form('drug_form'):
        brand          = st.text_input('商品名（必須）', value=target.get('brand', ''))
        generic        = st.text_input('一般名（成分名）', value=target.get('generic', ''))
        originator     = st.text_input('先発品名（ジェネリックの場合）', value=target.get('originator', ''))
        categories     = st.multiselect('タグ（複数選択可）', CATEGORIES, default=default_cats)
        purpose        = st.text_area('何のための薬ですか？', value=target.get('purpose', ''), height=80)
        usage          = st.text_area('飲み方・タイミング', value=target.get('usage', ''), height=80)
        side_effects   = st.text_area('副作用', value=target.get('sideEffects', ''), height=80)
        caution        = st.text_area('注意事項', value=target.get('caution', ''), height=80)
        doctor_comment = st.text_area('👨‍⚕️ ドクターコメント（任意）', value=target.get('doctorComment', ''), height=80)

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            submitted = st.form_submit_button('💾 保存', type='primary', use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button('キャンセル', use_container_width=True)

    if submitted:
        if not brand.strip():
            st.error('商品名は必須です')
        else:
            with st.spinner('GitHubに保存中...'):
                entry = {
                    'brand': brand, 'generic': generic, 'originator': originator,
                    'categories': categories,
                    'purpose': purpose, 'usage': usage,
                    'sideEffects': side_effects, 'caution': caution,
                    'doctorComment': doctor_comment
                }
                if is_edit and target:
                    target.update(entry)
                    target.pop('category', None)
                else:
                    entry['id'] = make_id()
                    drugs.append(entry)
                save_drugs(drugs)
                st.session_state.drugs = drugs
                st.session_state.mode = 'list'
            st.success('保存しました（GitHub・HTMLも自動更新済み）')
            st.rerun()

    if cancelled:
        st.session_state.mode = 'list'
        st.rerun()

# ===================================================================
# 薬一覧
# ===================================================================
else:
    col_search, col_cat = st.columns([3, 2])
    with col_search:
        q = st.text_input('🔍 薬名で検索', placeholder='例：アムロジピン')
    with col_cat:
        cat_filter = st.selectbox('タグで絞り込み', ['すべて'] + CATEGORIES)

    filtered = [
        d for d in drugs
        if (not q or q.lower() in d.get('brand','').lower() or q.lower() in d.get('generic','').lower())
        and (cat_filter == 'すべて' or cat_filter in get_categories(d))
    ]

    st.caption(f'表示中: {len(filtered)} 件 / 全 {len(drugs)} 件')

    if not filtered:
        st.info('該当する薬がありません')
    else:
        for d in filtered:
            cats = get_categories(d)
            primary = cats[0] if cats else ''
            cs = CAT_STYLES.get(primary, {'bg': 'rgba(0,0,0,0.06)', 'color': '#555', 'dot': '#aaa'})

            badges_html = ''.join([
                f'<span style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;'
                f'background:{CAT_STYLES.get(c, {}).get("bg","rgba(0,0,0,0.06)")};'
                f'color:{CAT_STYLES.get(c, {}).get("color","#555")};margin-left:4px;white-space:nowrap">{c}</span>'
                for c in cats
            ])

            col_card, col_edit, col_del = st.columns([10, 1, 1])
            has_comment = bool(d.get('doctorComment', '').strip())
            comment_badge = '<span style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;background:rgba(0,113,227,0.1);color:#0055b3;margin-left:6px;white-space:nowrap">👨‍⚕️ コメントあり</span>' if has_comment else ''

            with col_card:
                st.markdown(f"""
                <div style="background:#fff;border-radius:12px;padding:14px 16px;
                    box-shadow:rgba(0,0,0,0.08) 0 2px 8px;display:flex;
                    align-items:center;gap:12px;margin-bottom:2px;">
                    <div style="width:10px;height:10px;border-radius:50%;background:{cs['dot']};flex-shrink:0"></div>
                    <div style="flex:1;min-width:0">
                        <div style="font-size:15px;font-weight:600;color:#1d1d1f">{d.get('brand','')}{comment_badge}</div>
                        <div style="font-size:12px;color:rgba(0,0,0,0.48);margin-top:2px">{d.get('generic','')}{"　<span style='color:rgba(0,0,0,0.3)'>／</span> <span style='color:#888'>"+d['maker']+"</span>" if d.get('maker') else ''}{"　<span style='color:rgba(0,0,0,0.3)'>｜先発:</span> <span style='color:#888'>"+d['originator']+"</span>" if d.get('originator') else ''}</div>
                    </div>
                    <div style="display:flex;gap:0;flex-wrap:wrap;justify-content:flex-end">{badges_html}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_edit:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button('編集', key=f"edit_{d['id']}", use_container_width=True):
                    st.session_state.mode = 'edit'
                    st.session_state.edit_id = d['id']
                    st.rerun()

            with col_del:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                if st.button('削除', key=f"del_{d['id']}", use_container_width=True):
                    with st.spinner('削除中...'):
                        st.session_state.drugs = [x for x in drugs if x['id'] != d['id']]
                        save_drugs(st.session_state.drugs)
                    st.rerun()
