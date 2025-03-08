def simple_calculator(expression: str) -> str:
    """간단한 수식을 계산하는 함수"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return str(e)
