import configparser

class MyError:
    VERMELHO = '\033[31;1m'  # Código para vermelho escuro
    RESET = '\033[0m'   
    
    def __init__(self, et):
        self.config = configparser.RawConfigParser()
        self.config.read('ErrorMessages.properties', encoding='UTF-8')
        self.errorType = et

    def newError(self, optkey, key, **data):
        message = ''
        if optkey:
            return key
        if key:
            message = self.config.get(self.errorType, key)
        if data:
            for key, value in data.items():
                message = f"{message}, {key}: {value}"
        
        # Adiciona formatação de cor
        return f"{self.VERMELHO}{message}{self.RESET}"
