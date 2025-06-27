# from agents import Agent, handoff
# from pydantic import BaseModel

# @function_tool
# def perform_ocr(material: str) -> str:
    

# visual_analysis_agent = Agent(
#     name="VisualAnalysisAgent",
#     model="gpt-4o",
#     instructions="You are a visual analysis agent. You are given a list of materials and you need to analyze them.",
#     tools=[perform_ocr],
#     output_type=VisualAnalysis,
# )

# # keep visual analysis in context.
# analysis_agent = Agent(
#     name="AnalysisAgent",
#     instructions="You are a analysis agent. You are given a list of materials and you need to summarize them.",
#     tools=[
#         visual_analysis_agent.as_tool(
#             tool_name="visual_analysis",
#             tool_description="Analyze the diagrams and charts in the material.",
#         ),
#     ],
#     output_type=Summary,
#     model_settings=ModelSettings(tool_choice="required"), # if there are images
# )