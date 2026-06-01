# Tools package - Aggregates all tools from sub-modules
from src.tools.real_estate_tools import TOOLS as RE_TOOLS
from src.tools.mortgage_calculator import TOOLS as MORTGAGE_TOOLS
from src.tools.location_tools import TOOLS as LOCATION_TOOLS

# Combined tool registry for the Agent
ALL_TOOLS = RE_TOOLS + MORTGAGE_TOOLS + LOCATION_TOOLS
