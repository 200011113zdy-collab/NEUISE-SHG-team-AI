from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
from datetime import datetime

LOG_FILE = 'log.txt'

SYSTEM_PROMPT = '你是一个专业的AI助手。回复中涉及数学公式时，行内公式用$...$，块级公式用$$...$$格式书写。'

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(length))
        messages = body.get('messages', [])
        print(f"\n--- 收到 {len(messages)} 条消息 ---")

        parts = []
        # 【修改点 1】：把 System Prompt 直接塞进对话的最开头，当成背景设定告诉它
        parts.append(f"[系统指令]: {SYSTEM_PROMPT}")
        
        for m in messages:
            content = m.get('content', '').replace('\n', ' ').replace('\r', '')
            if m['role'] == 'user':
                parts.append(f"[用户]: {content}")
            elif m['role'] == 'assistant':
                parts.append(f"[AI]: {content}")
                
        parts.append("[AI]:")
        
        prompt = ' || '.join(parts)
        print(f"最终传给本地模型的 prompt:\n{prompt}")

        question = ''
        for m in reversed(messages):
            if m['role'] == 'user':
                question = m.get('content', '')
                break

        try:
            # 【修改点 2】：去掉了导致崩溃的 '--system' 参数，只传 '-p' 和 prompt
            result = subprocess.run(
                ['claude.cmd', '-p', prompt],
                capture_output=True, timeout=120
            )
            
            try:
                answer = result.stdout.decode('utf-8', errors='ignore').strip()
            except:
                answer = result.stdout.decode('gbk', errors='ignore').strip()

            stderr_output = result.stderr.decode('utf-8', errors='ignore').strip()
            if not stderr_output:
                stderr_output = result.stderr.decode('gbk', errors='ignore').strip()
            
            if stderr_output:
                print(f"⚠️ claude.cmd 输出了一些警告或错误:\n{stderr_output}")

            if not answer:
                print("❌ claude.cmd 没有返回任何内容！")
                answer = f"本地服务器调用失败，未返回内容。\n错误日志：{stderr_output}"

        except Exception as e:
            print(f"❌ 运行 subprocess 时发生严重错误: {str(e)}")
            answer = f"Python 服务器内部报错: {str(e)}"

        print(f"返回给前端的答复: {answer[:50]}...")

        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]\n')
            f.write(f'问：{question}\n')
            f.write(f'答：{answer}\n')
            f.write('-' * 40 + '\n')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'answer': answer
        }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass

print('Server running on http://localhost:8765')
HTTPServer(('localhost', 8765), Handler).serve_forever()