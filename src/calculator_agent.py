from logger import logger

def simple_calculator(expression: str) -> str:
    """간단한 수식을 계산하는 함수"""
    try:
        # 수식 검증 (허용된 문자만 포함)
        allowed_chars = "0123456789+-*/(). "
        if not all(char in allowed_chars for char in expression):
            raise ValueError("잘못된 문자 포함: 허용된 연산자는 +, -, *, /, () 입니다.")

        # eval() 실행 (보안 조치 적용)
        result = eval(expression, {"__builtins__": {}})
        
        # 계산 성공 시 로그 기록
        logger.write(f"✅ 계산 성공: {expression} = {result}\n")
        return str(result)
    
    except ZeroDivisionError:
        error_msg = "❌ 0으로 나눌 수 없습니다."
        logger.write(f"⚠️ 계산 오류 (ZeroDivisionError): {expression}\n")
        return error_msg
    
    except (SyntaxError, TypeError, ValueError) as e:
        error_msg = f"❌ 잘못된 수식입니다: {expression} | 오류 유형: {type(e).__name__}"
        logger.write(f"⚠️ 계산 오류 ({type(e).__name__}): {expression} | {e}\n")
        return error_msg
    
    except Exception as e:
        error_msg = "❌ 계산 중 알 수 없는 오류가 발생했습니다."
        logger.write(f"⛔ 예상치 못한 계산 오류: {expression} | {e}\n")
        return error_msg
