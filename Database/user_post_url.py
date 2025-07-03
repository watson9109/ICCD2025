#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バーチャル掲示板 - シンプル版
URLからイベント情報を抽出し、LLMを使って構造化します。
"""

import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# Gemini APIの設定
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    # Gemini APIの設定
    genai.configure(api_key=api_key)
else:
    print("警告: GEMINI_API_KEYが設定されていません。")
    print("1. Google AIスタジオ（https://aistudio.google.com/）でAPIキーを取得してください。")
    print("2. プロジェクトのルートディレクトリに.envファイルを作成し、以下の内容を記述してください：")
    print("   GEMINI_API_KEY=your_api_key_here")
    exit(1)


def fetch_html_content(url: str) -> str:
    """
    URLからHTMLコンテンツを取得する

    Args:
        url: 取得するWebページのURL

    Returns:
        HTMLの内容（テキスト形式）
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # エラーがあれば例外を発生させる
        return response.text
    except Exception as e:
        print(f"HTMLの取得に失敗しました: {e}")
        raise


def extract_text_from_html(html: str) -> str:
    """
    HTMLからテキストコンテンツを抽出する

    Args:
        html: HTMLコンテンツ

    Returns:
        抽出されたテキスト
    """
    soup = BeautifulSoup(html, "html.parser")
    
    # 不要な要素を削除
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    
    # 本文テキストを取得
    text = soup.get_text(separator="\n")
    
    # 余分な空白と改行を削除
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_event_info_with_llm(text: str, source_url: str) -> Dict[str, Any]:
    """
    LLMを使ってテキストからイベント情報を抽出する

    Args:
        text: 抽出元のテキスト
        source_url: 元のURL

    Returns:
        抽出されたイベント情報（辞書形式）
    """
    # 最新のGeminiモデルを使用
    model_name = "gemini-2.5-flash"
    
    # LLMに送信するプロンプト
    prompt = f"""
あなたは学内イベント情報を抽出するAIアシスタントです。
以下のテキストから、大学のイベント情報を抽出し、JSON形式で出力してください。

# 入力テキスト
{text}

# 抽出すべき情報
以下の情報を抽出し、JSONとして整形してください:
1. event_name: イベント名
2. event_date_start: イベント開始日時（ISO 8601形式：YYYY-MM-DDThh:mm:ss）
3. event_date_end: イベント終了日時（ISO 8601形式：YYYY-MM-DDThh:mm:ss）、不明な場合はnull
4. location: 開催場所
5. organizer: 主催団体
6. target_audience: 対象者、不明な場合はnull
7. summary: イベント内容の短い要約（100文字程度）
8. tags: イベント内容に関連するタグ（例: #講演会, #音楽, #スポーツ）を配列形式で

# 注意事項
- 情報が不足している場合は、合理的に推測してください。
- 日付や時間の情報は可能な限り正確に抽出してください。
- JSONはUTF-8でエンコードし、日本語文字列はエスケープしないでください。
- 今日の日付は2025年6月19日です。

# 出力形式
{{
  "event_name": "イベント名",
  "event_date_start": "YYYY-MM-DDThh:mm:ss",
  "event_date_end": "YYYY-MM-DDThh:mm:ss",
  "location": "開催場所",
  "organizer": "主催団体",
  "target_audience": "対象者",
  "description": "イベント内容の短い要約",
  "source_type": "url",
  "source_data": "{source_url}",
  "tags": ["#タグ1", "#タグ2", ...]
}}

JSONデータのみを出力してください。説明文やマークダウン記法は使用しないでください。
"""

    # LLMに問い合わせ
    try:
        # モデルをロード
        model = genai.GenerativeModel(model_name)
        
        # プロンプトの実行
        response = model.generate_content(prompt)
        
        # レスポンスから JSON を抽出
        json_str = response.text
        # JSON部分のみを抽出（マークダウンのコードブロックが含まれている可能性があるため）
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        # JSONをパース
        event_data = json.loads(json_str)
        return event_data
    except Exception as e:
        print(f"イベント情報の抽出に失敗しました: {e}")
        # 基本的な情報を返す
        return {
            "error": str(e),
            "source_type": "url",
            "source_data": source_url
        }


def save_to_json(event_data: Dict[str, Any], filename: str) -> None:
    """
    イベントデータをJSONファイルに保存する

    Args:
        event_data: 保存するイベントデータ
        filename: 保存先のファイル名
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(event_data, f, ensure_ascii=False, indent=2)
    
    print(f"イベント情報を {filename} に保存しました。")


# メイン処理
def main():
    # URLを指定
    url = "https://www.uec.ac.jp/news/event/2025/20250613_7027.html"  # ここに解析したいイベントページのURLを指定
    output_file = "event_data.json"  # 出力ファイル名
    
    try:
        print(f"URLからイベント情報を抽出しています: {url}")
        
        # HTMLを取得
        html = fetch_html_content(url)
        
        # HTMLからテキストを抽出
        text = extract_text_from_html(html)
        
        # テキストからイベント情報を抽出
        event_data = extract_event_info_with_llm(text, url)
        
        # 結果を表示
        print("\n===== イベント情報 =====")
        print(json.dumps(event_data, ensure_ascii=False, indent=2))
        print("=======================\n")
        
        # JSONファイルに保存
        save_to_json(event_data, output_file)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()
