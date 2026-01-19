import streamlit as st
import pandas as pd
import altair as alt
from main import run_text_to_sql

# --- Config ---
st.set_page_config(
    page_title="AI Chatbot DB", 
    page_icon="📊", 
    layout="wide"
)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=100)
    st.title("🗄️ Database Info")
    st.info("Status: Connected 🟢\nDB: baogia_db (PostgreSQL)")
    
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.caption("Powered by: Python + PocketFlow + Gemini 2.5 Flash")
    st.caption("Build by LongLu")

# --- Main ---
st.title("📊 Trợ lý SQL")
st.markdown("Hỏi đáp dữ liệu & Trực quan hóa biểu đồ.")

if "messages" not in st.session_state:
    st.session_state.messages = []

def render_chart_options(df, unique_key):
    """
    Hàm hiển thị tùy chọn vẽ biểu đồ.
    unique_key: Để phân biệt widget của các tin nhắn khác nhau.
    """
    if df.empty:
        return

    # Lọc cột
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object', 'datetime', 'category']).columns.tolist()

    if numeric_cols:
        with st.expander(f"📈 Trực quan hóa dữ liệu (Biểu đồ)", expanded=False):
            c1, c2, c3 = st.columns(3)
            
            with c1:
                chart_type = st.selectbox(
                    "Loại biểu đồ:", 
                    ["Bar Chart (Cột)", "Line Chart (Đường)", "Area Chart (Vùng)", "Scatter (Phân tán)"],
                    key=f"type_{unique_key}" # Key duy nhất
                )
            
            with c2:
                x_axis = st.selectbox(
                    "Trục X:", 
                    options=categorical_cols + numeric_cols,
                    index=0 if categorical_cols else 0,
                    key=f"x_{unique_key}"
                )
            
            with c3:
                y_axis = st.selectbox(
                    "Trục Y:", 
                    options=numeric_cols,
                    index=0,
                    key=f"y_{unique_key}"
                )
            
            # Vẽ chart
            if x_axis and y_axis:
                chart_data = df[[x_axis, y_axis]].set_index(x_axis)
                
                try:
                    if "Bar" in chart_type:
                        st.bar_chart(chart_data, color="#FF4B4B")
                    elif "Line" in chart_type:
                        st.line_chart(chart_data, color="#29B5E8")
                    elif "Area" in chart_type:
                        st.area_chart(chart_data, color="#FFA07A")
                    elif "Scatter" in chart_type:
                        c = alt.Chart(df).mark_circle(size=60).encode(
                            x=x_axis, y=y_axis, tooltip=[x_axis, y_axis]
                        ).interactive()
                        st.altair_chart(c, use_container_width=True)
                except Exception as e:
                    st.error(f"Không thể vẽ biểu đồ: {e}")

# --- Hiển thị lịch sử chat ---
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if isinstance(message["content"], pd.DataFrame):
            st.dataframe(message["content"])
            
            render_chart_options(message["content"], unique_key=f"msg_{i}")
            
        else:
            st.markdown(message["content"])
        
        if message.get("sql_debug"):
            with st.expander("🔍 Code SQL"):
                st.code(message["sql_debug"], language="sql")

# --- Xử lý Input ---
if prompt := st.chat_input("VD: Top 5 dự án giá trị lớn nhất?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Đang phân tích..."):
            try:
                response = run_text_to_sql(prompt)
                
                if isinstance(response, tuple):
                    data, columns, generated_sql = response
                    
                    if not data:
                        msg = "Không tìm thấy dữ liệu."
                        st.warning(msg)
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                    else:
                        df = pd.DataFrame(data, columns=columns)
                        
                        st.markdown(f"✅ Tìm thấy **{len(data)}** kết quả:")
                        st.dataframe(df)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": df,
                            "sql_debug": generated_sql 
                        })
                        
                        st.rerun() 
                else:
                    st.error(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
            except Exception as e:
                st.error(f"Lỗi: {e}")