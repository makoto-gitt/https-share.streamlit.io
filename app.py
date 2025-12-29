import streamlit as st
import pandas as pd
import jaconv
import os

# --- ページ設定 ---
st.set_page_config(
    page_title="医薬品検索",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- スマホ対応CSS設定 ---
st.markdown("""
<style>
    /* 全体のフォント・余白調整 */
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .main .block-container { padding: 1rem 0.5rem; max-width: 100%; }
    
    /* ヘッダー */
    .app-header {
        text-align: center;
        padding: 0.5rem 0;
        margin-bottom: 0.5rem;
    }
    .app-title {
        font-size: 1.4rem;
        font-weight: 700;
        margin: 0;
        color: var(--text-color);
    }
    .app-subtitle {
        font-size: 0.7rem;
        color: #888;
        margin-top: 2px;
    }
    
    /* 検索入力欄 */
    .stTextInput > div > div > input {
        font-size: 16px !important;
        padding: 12px !important;
        border-radius: 10px !important;
    }
    
    /* トグル調整 */
    .stToggle { margin-top: 0.5rem; }
    
    /* 薬品カード - スマホ最適化 */
    .drug-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 1px solid #e0e0e0;
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    @media (prefers-color-scheme: dark) {
        .drug-card {
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            border-color: #404040;
        }
    }
    
    .drug-name {
        font-size: 1rem;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: var(--text-color);
        line-height: 1.3;
        word-break: break-all;
    }
    
    /* バッジ類 */
    .badge-row { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
    
    .category-badge {
        font-size: 0.65rem;
        padding: 2px 6px;
        border-radius: 4px;
        background: #6c757d;
        color: white;
        font-weight: 600;
    }
    
    .type-badge {
        font-size: 0.65rem;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 600;
    }
    .badge-original { background: #198754; color: white; }
    .badge-generic { background: #0d6efd; color: white; }
    .badge-other { background: #adb5bd; color: #212529; }
    
    .reg-badge {
        font-size: 0.65rem;
        padding: 2px 6px;
        border-radius: 4px;
        background: #ffc107;
        color: #212529;
        font-weight: 600;
    }
    
    /* 詳細情報 */
    .card-info {
        font-size: 0.75rem;
        color: #666;
        line-height: 1.4;
    }
    .card-info div { margin-bottom: 2px; }
    
    .price-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #e0e0e0;
    }
    @media (prefers-color-scheme: dark) {
        .price-row { border-color: #404040; }
    }
    
    .price-tag {
        font-size: 1.1rem;
        font-weight: 700;
        color: #dc3545;
    }
    
    /* 検索結果カウント */
    .result-count {
        text-align: center;
        font-size: 0.8rem;
        color: #666;
        margin: 0.5rem 0;
    }
    
    /* Streamlitデフォルト要素の調整 */
    .stMarkdown hr { margin: 0.5rem 0; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem; }
</style>
""", unsafe_allow_html=True)

# CSVファイルのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "内用薬": os.path.join(BASE_DIR, "内用薬.csv"),
    "外用薬": os.path.join(BASE_DIR, "外用薬.csv"),
    "注射薬": os.path.join(BASE_DIR, "注射薬.csv")
}

@st.cache_data
def load_data():
    dfs = []
    for category, filename in FILES.items():
        if not os.path.exists(filename): continue
        
        df = None
        for enc in ['utf-8-sig', 'utf-8', 'shift_jis', 'cp932', 'euc-jp']:
            try:
                df = pd.read_csv(filename, encoding=enc)
                break
            except: continue
        
        if df is None: continue

        df['診療区分'] = category
        
        if '品名' in df.columns:
            name_col_idx = df.columns.get_loc('品名')
            flag_cols = df.iloc[:, name_col_idx-3 : name_col_idx]
            df['毒劇麻区分'] = flag_cols.fillna('').astype(str).apply(lambda x: ''.join(x), axis=1)
            df['毒劇麻区分'] = df['毒劇麻区分'].replace('', '普通薬')
            try:
                df['規格'] = df.iloc[:, name_col_idx-4].fillna('')
            except:
                df['規格'] = ''
        else:
            df['毒劇麻区分'] = '不明'
            df['規格'] = ''

        def determine_ge_type(row):
            original_flg = ""
            generic_flg = ""
            for col in df.columns:
                if "先発医薬品" in col and "後発医薬品" not in col:
                    original_flg = str(row[col])
                if "診療報酬" in col and "後発医薬品" in col:
                    generic_flg = str(row[col])
            
            if "先発品" in original_flg: return "先発品"
            elif "後発品" in generic_flg or "★" in generic_flg: return "後発品(GE)"
            elif "先発品" in generic_flg: return "先発品"
            else: return "-" 

        df['先発/GE'] = df.apply(determine_ge_type, axis=1)
        
        for c in ['成分名', 'メーカー名', '薬価']:
            if c not in df.columns: df[c] = '-'
                
        dfs.append(df)
    
    if dfs: return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

def render_card(row):
    ge_type = row['先発/GE']
    if '先発' in ge_type:
        ge_class, ge_label = 'badge-original', '先発'
    elif '後発' in ge_type:
        ge_class, ge_label = 'badge-generic', 'GE'
    else:
        ge_class, ge_label = 'badge-other', '他'

    reg_type = row['毒劇麻区分']
    reg_html = f'<span class="reg-badge">{reg_type}</span>' if reg_type not in ['普通薬', 'nan', ''] else ""

    try: price = f"¥{float(row['薬価']):,.1f}"
    except: price = str(row['薬価'])

    html = f"""
<div class="drug-card">
<div class="drug-name">{row['品名']}</div>
<div class="badge-row">
<span class="category-badge">{row['診療区分']}</span>
<span class="type-badge {ge_class}">{ge_label}</span>
{reg_html}
</div>
<div class="card-info">
<div>📏 {row['規格']}</div>
<div>🏭 {row['メーカー名']}</div>
<div>🧪 {row['成分名']}</div>
</div>
<div class="price-row">
<span>薬価</span>
<span class="price-tag">{price}</span>
</div>
</div>
"""
    return html

def main():
    # ヘッダー
    st.markdown("""
    <div class="app-header">
        <p class="app-title">💊 医薬品検索</p>
        <p class="app-subtitle">データ: 2025.12.5 時点</p>
    </div>
    """, unsafe_allow_html=True)
    
    df = load_data()
    if df.empty:
        st.error("データ読み込みエラー")
        return

    # 検索欄
    search_query = st.text_input("", placeholder="薬名を入力（ひらがなOK）", label_visibility="collapsed")
    exclude_mix = st.toggle("配合剤を除外", value=True)

    if search_query:
        query_katakana = jaconv.hira2kata(search_query)
        
        mask = (
            df['品名'].astype(str).str.contains(query_katakana, case=False, na=False) | 
            df['成分名'].astype(str).str.contains(query_katakana, case=False, na=False) |
            df['品名'].astype(str).str.contains(search_query, case=False, na=False)
        )
        results = df[mask]
        
        if not results.empty:
            found_ingredients = results['成分名'].dropna().unique()
            found_ingredients = [x for x in found_ingredients if x not in ['', 'nan']]
            if found_ingredients:
                mask_extended = df['成分名'].isin(found_ingredients)
                results = pd.concat([results, df[mask_extended]]).drop_duplicates(subset=['品名', '成分名'])
        
        if exclude_mix:
            mask_exclude = (
                results['品名'].astype(str).str.contains('配合', case=False, na=False) |
                results['成分名'].astype(str).str.contains('・', case=False, na=False)
            )
            results = results[~mask_exclude]

        cnt = len(results)
        if cnt > 0:
            st.markdown(f'<p class="result-count">🔍 {cnt}件 ヒット</p>', unsafe_allow_html=True)
            max_display = 50
            if cnt > max_display:
                st.warning(f"上位{max_display}件を表示")
                results = results.head(max_display)

            for _, row in results.iterrows():
                st.markdown(render_card(row), unsafe_allow_html=True)
        else:
            st.info("見つかりませんでした")
            if exclude_mix:
                st.caption("※配合剤除外がONです")

if __name__ == "__main__":
    main()
