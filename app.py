import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 配置
MODEL_PATH = "zoomerwork/model_usingultrachat"

print("🔄 正在加载模型...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
)

# 设置pad_token（如果没有的话）
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("✅ 模型加载完成!")

def chat(message, history):
    try:
        # 构建对话历史
        conversation = ""
        
        # 处理不同格式的history
        if history:
            # 只保留最近的5轮对话
            recent_history = history[-5:] if len(history) > 5 else history
            
            for item in recent_history:
                # 兼容不同的history格式
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    user_msg, bot_msg = item
                    conversation += f"User: {user_msg}\nAssistant: {bot_msg}\n"
                elif isinstance(item, dict):
                    # 有些版本使用字典格式
                    user_msg = item.get('user', item.get('role') == 'user' and item.get('content', ''))
                    bot_msg = item.get('assistant', item.get('role') == 'assistant' and item.get('content', ''))
                    if user_msg and bot_msg:
                        conversation += f"User: {user_msg}\nAssistant: {bot_msg}\n"
        
        conversation += f"User: {message}\nAssistant:"
        
        # Tokenize
        inputs = tokenizer(
            conversation, 
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=2048
        )
        
        # 移动到正确的设备
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # 生成回复
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # 解码
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # 提取assistant的回复
        if "Assistant:" in full_response:
            response = full_response.split("Assistant:")[-1].strip()
        else:
            response = full_response.strip()
        
        # 清理多余内容
        if "User:" in response:
            response = response.split("User:")[0].strip()
        
        return response
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        print(f"History 格式: {type(history)}")
        if history:
            print(f"History 内容示例: {history[:2]}")  # 打印前2个元素看格式
        import traceback
        traceback.print_exc()
        return f"抱歉，发生了错误: {str(e)}"

# 创建界面
demo = gr.ChatInterface(
    fn=chat,
    title="🤖 Chatbot",
    description="基于LLM微调的对话模型",
    examples=[
        "Hello",
        "Can you help me to write some python code?",
        "Explain what is ML",
    ],
)

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
    )