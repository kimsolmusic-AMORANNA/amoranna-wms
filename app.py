# ---------------------------------------------------------
# 아모란나 창고 관리 앱 (기초 + 관리자 화면 업그레이드 버전)
# - 기술 스택: Python, Streamlit, gspread, Google Service Account
# ---------------------------------------------------------

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import io
import json  # ✨ 비밀 금고를 열기 위한 도구 추가

# ---------------------------------------------------------
# ✨ 마법 24탄: 여백 정상화 및 모바일 스크롤 유지
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* 여백을 2.5rem으로 살짝 늘려서 제목 윗부분 잘림 방지 */
    .block-container { 
        padding-top: 2.5rem; 
        padding-bottom: 1rem; 
    }
    /* 모바일 표 터치 스크롤 허용 */
    div[data-testid="stDataFrameResizable"], div[data-testid="stDataFrame"] {
        touch-action: pan-y !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 1. 구글 스프레드시트 연결 설정 부분 (웹 배포용으로 변경됨 ✨)
# ---------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ✨ 인터넷 비밀 금고(Secrets)에서 key.json 내용을 가져옵니다.
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES
    )

    gc = gspread.authorize(credentials)
    SPREADSHEET_NAME = "그로스 체크리스트"
    sh = gc.open(SPREADSHEET_NAME)
    connected = True 
except Exception as e:
    sh = None
    connected = False
    error_message = str(e)


# ---------------------------------------------------------
# 2. Streamlit 기본 화면 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="아모란나 물류팀 입고관리",
    page_icon="📦",
    layout="wide"
)

# 메인 제목
st.markdown("### 📦 아모란나 물류팀 입고관리")

if connected:
    st.success("✅ 구글 스프레드시트 연결 성공: '그로스 체크리스트'")
else:
    st.warning("⚠️ 구글 스프레드시트에 연결하지 못했습니다. 비밀 금고(Secrets) 설정을 확인하세요.")
    if not connected:
        st.write("에러 상세 내용:", error_message)

# ---------------------------------------------------------
# 3. 상단 가로 라디오 버튼으로 모드 선택 만들기
# ---------------------------------------------------------
mode = st.radio(
    "",
    ("작업자", "관리자"),
    horizontal=True,
    label_visibility="collapsed",
)

if "table_key" not in st.session_state:
    st.session_state["table_key"] = 0

if "save_success" not in st.session_state:
    st.session_state["save_success"] = False


# ---------------------------------------------------------
# 4. 선택한 모드에 따라 화면 보여주기
# ---------------------------------------------------------
if mode == "관리자":
    st.subheader("👨‍💼 관리자 모드")
    st.markdown("<h4 style='color:gray;'>작업 지시 및 현황 확인</h4>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 작업 지시 날짜 선택")
    order_date = st.date_input(
        "작업 지시 날짜를 선택하세요.",
        help="이 작업 지시서가 적용될 날짜를 선택하세요."
    )
    st.info(f"선택한 작업 지시 날짜: {order_date}")
    st.markdown("---")

    st.markdown("### 📋 작업 지시 내용 입력 (엑셀처럼 자유롭게 작성)")

    initial_rows = 5
    df_initial = pd.DataFrame(
        {
            "옵션 ID": ["" for _ in range(initial_rows)],
            "품명": ["" for _ in range(initial_rows)],
            "목표 수량": ["" for _ in range(initial_rows)],
            "코멘트": ["" for _ in range(initial_rows)],
        }
    )

    edited_df = st.data_editor(
        df_initial,
        num_rows="dynamic",
        use_container_width=True,
        key=f"admin_order_table_{st.session_state['table_key']}",
    )

    st.markdown("---")
    st.markdown("### ✅ 작업 지시서 저장")

    if st.button("작업 지시서 구글 시트로 보내기", type="primary"):
        def is_not_empty_cell(value):
            if value is None: return False
            if isinstance(value, str) and value.strip() == "": return False
            return True

        mask_valid_rows = edited_df.apply(
            lambda row: any(is_not_empty_cell(row[col]) for col in ["옵션 ID", "품명", "목표 수량", "코멘트"]),
            axis=1,
        )

        valid_df = edited_df[mask_valid_rows].copy()

        if valid_df.empty:
            st.warning("⚠️ 저장할 데이터가 없습니다. 표에 내용을 입력해 주세요.")
        else:
            order_date_str = str(order_date)
            valid_df["지시날짜"] = order_date_str
            valid_df["관리자 코멘트"] = valid_df["코멘트"]
            valid_df["작업상태"] = "작업준비"
            valid_df["완료수량"] = ""
            valid_df["작업자"] = ""
            valid_df["작업자 코멘트"] = ""

            ordered_df = valid_df[["지시날짜", "옵션 ID", "품명", "목표 수량", "관리자 코멘트", "작업상태", "완료수량", "작업자", "작업자 코멘트"]]
            rows_to_append = ordered_df.values.tolist()

            try:
                ws = sh.worksheet("작업지시서")
                ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                st.session_state["save_success"] = True
                st.session_state["table_key"] += 1
                st.rerun()
            except Exception as e:
                st.error("구글 시트에 저장하는 중 오류가 발생했습니다.")
                st.write(e)

    if st.session_state.get("save_success", False):
        st.success("🎉 성공적으로 저장되었습니다!")
        st.session_state["save_success"] = False

elif mode == "작업자":
    if not connected:
        st.error("구글 시트가 연결되지 않아 데이터를 불러올 수 없습니다.")
    else:
        try:
            ws_job = sh.worksheet("그로스 입고관리")
            all_values = ws_job.get_all_values()
        except Exception as e:
            st.error("구글 시트를 불러오는 중 오류가 발생했습니다.")
        else:
            if not all_values or len(all_values) <= 2:
                st.info("현재 등록된 작업 지시가 없습니다.")
            else:
                title_row = all_values[0]
                header = all_values[1]
                rows = all_values[2:]

                df_all = pd.DataFrame(rows, columns=header)
                df_all = df_all.fillna("")

                if "작업상태" in df_all.columns:
                    df_all["작업상태"] = df_all["작업상태"].astype(str).str.strip()
                    df_all.loc[df_all["작업상태"] == "", "작업상태"] = "작업대기"

                sheet_row_map = {idx: idx + 3 for idx in range(len(df_all))}

                import datetime as _dt
                today = _dt.date.today()

                date_range = st.date_input(
                    "📅 작업 기간 선택", 
                    value=(today, today),
                    label_visibility="visible"
                )

                if isinstance(date_range, tuple) or isinstance(date_range, list):
                    start_date, end_date = date_range
                else:
                    start_date = end_date = date_range

                if start_date > end_date:
                    start_date, end_date = end_date, start_date

                if "날짜" not in df_all.columns:
                    st.error("구글 시트에 '날짜' 컬럼이 없습니다.")
                else:
                    df_all["날짜"] = df_all["날짜"].astype(str).str.strip()
                    df_all["_날짜_dt"] = pd.to_datetime(df_all["날짜"], format="%Y/%m/%d", errors="coerce")

                    start_ts = pd.to_datetime(start_date)
                    end_ts = pd.to_datetime(end_date)
                    date_mask = (df_all["_날짜_dt"] >= start_ts) & (df_all["_날짜_dt"] <= end_ts)

                    if not date_mask.any():
                        st.info("선택한 기간에 해당하는 작업 지시가 없습니다.")
                    else:
                        filtered_df = df_all[date_mask].copy()
                        filtered_df["_날짜_str"] = filtered_df["날짜"].astype(str).str.strip()

                        display_cols = [
                            "날짜", "옵션 ID", "품목명", "목표수량", 
                            "완료수량", "작업상태", "작업자", "지시사항", "작업자 코멘트"
                        ]

                        missing_cols = [c for c in display_cols if c not in filtered_df.columns]
                        if missing_cols:
                            st.error(f"시트에 다음 컬럼이 없습니다: {missing_cols}")
                        else:
                            sorted_df = filtered_df.sort_values("_날짜_dt").copy()
                            filtered_sheet_rows = [sheet_row_map[i] for i in sorted_df.index]

                            original_view_df = sorted_df[display_cols].copy().reset_index(drop=True)
                            original_view_df = original_view_df.astype(str)
                            original_view_df = original_view_df.replace(to_replace=["None", "nan", "NaN", "<NA>"], value="")

                            unique_dates = original_view_df['날짜'].unique()
                            date_color_map = {}
                            for i, date_val in enumerate(unique_dates):
                                if i % 2 == 0:
                                    date_color_map[date_val] = "background-color: #ffffff"
                                else:
                                    date_color_map[date_val] = "background-color: #f2f6fc"

                            def apply_row_styles(row):
                                status = str(row['작업상태']).strip()
                                if status == '작업완료':
                                    color = "background-color: #ccffcc" # 형광 연두색
                                else:
                                    color = date_color_map.get(row['날짜'], '')
                                return [color] * len(row)

                            styled_df = original_view_df.style.apply(apply_row_styles, axis=1)

                            st.write("") # 약간의 여백
                            col1, col2, col3 = st.columns([2.5, 1, 1.5])
                            with col1:
                                st.markdown("#### 📋 작업 목록")
                            with col2:
                                if st.button("🔄 새로고침", key="refresh_all"):
                                    st.rerun()
                            with col3:
                                try:
                                    buffer = io.BytesIO()
                                    original_view_df.to_excel(buffer, index=False)
                                    buffer.seek(0)
                                    filename = f"입고관리_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

                                    st.download_button(
                                        "📥 엑셀 저장",
                                        data=buffer,
                                        file_name=filename,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_all"
                                    )
                                except Exception as e:
                                    st.error(f"엑셀 오류: {e}")

                            column_config = {
                                "날짜": st.column_config.TextColumn("날짜", disabled=True),
                                "옵션 ID": st.column_config.TextColumn("옵션 ID", disabled=True),
                                "품목명": st.column_config.TextColumn("품목명", disabled=True),
                                "목표수량": st.column_config.TextColumn("목표수량", disabled=True, width="small"),
                                "완료수량": st.column_config.TextColumn("완료수량", width="small"),
                                "작업상태": st.column_config.SelectboxColumn(
                                    "작업상태",
                                    options=["작업대기", "작업준비", "작업완료", "작업불가(재고부족)", "작업연기", "기타"],
                                    required=True,
                                ),
                                "작업자": st.column_config.SelectboxColumn(
                                    "작업자",
                                    options=["유은미", "김정음", "박준수", "김솔", "이승환", "김태주", "기타"], 
                                ),
                                "지시사항": st.column_config.TextColumn("지시사항"),
                                "작업자 코멘트": st.column_config.TextColumn("작업자 코멘트", width=300),
                            }

                            edited_jobs_df = st.data_editor(
                                styled_df,
                                column_config=column_config,
                                use_container_width=False, 
                                num_rows="dynamic",
                                height=500,
                                key="worker_table_all",
                            )

                            try:
                                if not edited_jobs_df.equals(original_view_df):
                                    changed_mask = (edited_jobs_df != original_view_df).any(axis=1)
                                    for local_idx, changed in enumerate(changed_mask):
                                        if not changed: continue

                                        sheet_row = filtered_sheet_rows[local_idx]
                                        row_values = edited_jobs_df.iloc[local_idx][display_cols].tolist()

                                        cell_range = f"A{sheet_row}:I{sheet_row}"
                                        ws_job.update(cell_range, [row_values], value_input_option="USER_ENTERED")
                            except Exception as e:
                                st.error(f"저장 중 에러 발생: {e}")