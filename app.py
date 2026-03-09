from transformers import pipeline
import gradio as gr

summarizer = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    tokenizer="facebook/bart-large-cnn",
    framework="pt",                   # PyTorch
    device=-1                         # CPU (0/1/... if you have GPU)
)

def predict(prompt: str):
    result = summarizer(
        prompt,
        truncation=True,              # keep within 1024 token input limit
        max_new_tokens=256,
        min_new_tokens=32,
        no_repeat_ngram_size=3
    )[0]["summary_text"]
    return result

gr.Interface(
    fn=predict,
    inputs=gr.Textbox(lines=8, label="Text"),
    outputs=gr.Textbox(label="Summary"),
).launch()
