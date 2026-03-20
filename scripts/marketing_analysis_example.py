#!/usr/bin/env python3
"""
营销数据分析 Agent 示例
使用 AI Data Science Team 分析 Excel/CSV 营销数据
"""

import pandas as pd


def analyze_marketing_data(file_path: str, questions: list[str]):
    """
    分析营销数据

    参数:
        file_path: Excel 或 CSV 文件路径
        questions: 要分析的问题列表
    """
    print(f"📊 正在分析营销数据: {file_path}")
    print("=" * 60)

    # 1. 加载数据
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        raise ValueError("不支持的文件格式，请使用 Excel (.xlsx, .xls) 或 CSV (.csv)")

    print(f"✅ 数据加载成功: {df.shape[0]} 行 x {df.shape[1]} 列")
    print(f"列名: {', '.join(df.columns.tolist())}")
    print()

    # 2. 初始化 LLM (使用本地 Ollama)
    print("🤖 初始化 AI Agent...")
    try:
        from ai_data_science_team import PandasDataAnalyst
        from ai_data_science_team.agents import DataWranglingAgent, DataVisualizationAgent
        from langchain_ollama import ChatOllama
    except ImportError as e:
        print(f"❌ 缺少可选依赖: {e}")
        print("请先安装: pip install ai-data-science-team langchain-ollama")
        return

    llm = ChatOllama(model="llama3.1:8b", temperature=0)

    # 3. 创建分析 Agent
    wrangling_agent = DataWranglingAgent(llm=llm)
    viz_agent = DataVisualizationAgent(llm=llm)

    analyst = PandasDataAnalyst(
        model=llm,
        data_wrangling_agent=wrangling_agent,
        data_visualization_agent=viz_agent
    )

    # 4. 执行分析
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*60}")
        print(f"问题 {i}: {question}")
        print(f"{'='*60}")

        try:
            response = analyst.invoke_agent(
                user_instructions=f"""
                请分析以下营销数据，回答这个问题：{question}

                可用的数据列: {', '.join(df.columns.tolist())}

                请提供：
                1. 数据分析结果
                2. 可视化图表（如果适用）
                3. 关键洞察和建议
                """,
                data_raw=df.to_dict(orient='records')
            )

            # 获取处理后的数据
            wrangled_data = analyst.get_data_wrangled()

            if wrangled_data is not None:
                print("\n📈 分析结果:")
                print(wrangled_data.to_string(index=False))

                # 获取可视化
                plot = analyst.get_plotly_graph()
                if plot is not None:
                    plot.show()
                    print("\n✅ 图表已生成")

        except Exception as e:
            print(f"\n❌ 分析出错: {e}")

    print(f"\n{'='*60}")
    print("✅ 分析完成！")


# 使用示例
if __name__ == "__main__":
    # 你的营销数据文件路径
    DATA_FILE = "raw_data/202601.xlsx"  # 替换为你的文件

    # 你想回答的业务问题
    BUSINESS_QUESTIONS = [
        "按产品类别统计销售额，找出最畅销的产品",
        "分析每月的销售趋势",
        "计算各产品的平均售价和总销售额",
    ]

    # 运行分析
    analyze_marketing_data(DATA_FILE, BUSINESS_QUESTIONS)
