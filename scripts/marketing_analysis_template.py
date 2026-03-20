#!/usr/bin/env python3
"""
营销数据分析快速模板
适用于 Excel/CSV 文件的业务数据分析
"""

import pandas as pd


# ============ 配置区域 ============

# 1. 数据文件路径（修改为你的文件）
DATA_FILE = "raw_data/202601.xlsx"

# 2. 业务问题（修改为你想分析的问题）
QUESTIONS = [
    "哪个产品销售额最高？",
    "每月销售趋势如何？",
    "各产品的平均利润率是多少？",
]

# 3. LLM 配置
# 选项 A: 使用本地 Ollama (免费，需先安装)
USE_LOCAL_LLM = True
OLLAMA_MODEL = "llama3.1:8b"

# 选项 B: 使用 OpenAI API (需 API key)
# USE_LOCAL_LLM = False
# OPENAI_API_KEY = "your-api-key-here"
# OPENAI_MODEL = "gpt-4o-mini"

# ============ 分析代码 ============

def main():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║       营销数据分析 AI Agent                              ║
    ║   Marketing Data Analysis with AI Agents               ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # 1. 加载数据
    print(f"\n📂 加载数据: {DATA_FILE}")
    try:
        if DATA_FILE.endswith('.xlsx'):
            df = pd.read_excel(DATA_FILE)
        else:
            df = pd.read_csv(DATA_FILE)
        print(f"   ✅ {df.shape[0]} 行 × {df.shape[1]} 列")
        print(f"   列: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return

    # 2. 初始化 LLM
    print(f"\n🤖 初始化 AI 模型...")
    try:
        from ai_data_science_team import (
            PandasDataAnalyst,
            DataWranglingAgent,
            DataVisualizationAgent,
        )
        from langchain_ollama import ChatOllama
    except ImportError as e:
        print(f"   ❌ 缺少可选依赖: {e}")
        print("   请先安装: pip install ai-data-science-team langchain-ollama")
        return

    if USE_LOCAL_LLM:
        llm = ChatOllama(model=OLLAMA_MODEL, temperature=0)
        print(f"   ✅ 使用本地模型: {OLLAMA_MODEL}")
        print(f"   💡 提示: 首次使用需要 'ollama pull {OLLAMA_MODEL}'")
    else:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL)
        print(f"   ✅ 使用 OpenAI: {OPENAI_MODEL}")

    # 3. 创建 Agent
    print(f"\n🔧 创建分析 Agent...")
    wrangling_agent = DataWranglingAgent(llm=llm)
    viz_agent = DataVisualizationAgent(llm=llm)
    analyst = PandasDataAnalyst(
        model=llm,
        data_wrangling_agent=wrangling_agent,
        data_visualization_agent=viz_agent,
    )
    print(f"   ✅ Agent 就绪")

    # 4. 执行分析
    print(f"\n" + "="*60)
    print(f"📊 开始分析")
    print(f"="*60)

    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n问题 {i}/{len(QUESTIONS)}: {question}")
        print("-" * 60)

        try:
            response = analyst.invoke_agent(
                user_instructions=f"""
                基于给定的数据，回答以下业务问题：{question}

                数据列: {', '.join(df.columns.tolist())}

                请：
                1. 提供清晰的数据分析结果
                2. 如果适合可视化，生成图表
                3. 给出可执行的业务建议
                """,
                data_raw=df.to_dict(orient='records')
            )

            # 显示结果
            result = analyst.get_data_wrangled()
            if result is not None and not result.empty:
                print("\n结果:")
                print(result.head(10).to_string(index=False))
                if len(result) > 10:
                    print(f"... (共 {len(result)} 行)")

            # 显示图表
            plot = analyst.get_plotly_graph()
            if plot is not None:
                print("\n📈 生成图表...")
                plot.show()

            print("\n✅ 完成")

        except Exception as e:
            print(f"\n❌ 分析失败: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n" + "="*60)
    print(f"✅ 所有分析完成！")
    print(f"="*60)


if __name__ == "__main__":
    main()
