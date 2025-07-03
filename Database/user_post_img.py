#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バーチャル掲示板 - 画像版
イベントチラシ画像からイベント情報を抽出し、LLMを使って構造化します。
"""

import os
import json
from datetime import datetime
import google.generativeai as genai
from typing import Dict, Any
from dotenv import load_dotenv
from PIL import Image

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


def load_image(image_path: str) -> Image.Image:
    """
    画像ファイルを読み込む

    Args:
        image_path: 読み込む画像ファイルのパス

    Returns:
        PIL Imageオブジェクト
    """
    try:
        # 画像ファイルの存在確認
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # 画像を読み込み
        image = Image.open(image_path)
        
        # RGBモードに変換（必要に応じて）
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        print(f"画像を読み込みました: {image_path} (サイズ: {image.size})")
        return image
        
    except Exception as e:
        print(f"画像の読み込みに失敗しました: {e}")
        raise


def extract_event_info_from_image(image: Image.Image, image_path: str) -> Dict[str, Any]:
    """
    Gemini Vision APIを使って画像からイベント情報を抽出する

    Args:
        image: PIL Imageオブジェクト
        image_path: 元の画像ファイルパス

    Returns:
        抽出されたイベント情報（辞書形式）
    """
    # 最新のGeminiモデルを使用（Vision対応）
    model_name = "gemini-2.5-flash"
    
    # LLMに送信するプロンプト
    prompt = """
あなたは学内イベント情報を抽出するAIアシスタントです。
提供された画像（イベントチラシ）から、大学のイベント情報を抽出し、JSON形式で出力してください。

# 抽出すべき情報
以下の情報を抽出し、JSONとして整形してください:
1. event_name: イベント名（画像から読み取れない場合はnull）
2. event_date_start: イベント開始日時（ISO 8601形式：YYYY-MM-DDThh:mm:ss、読み取れない場合はnull）
3. event_date_end: イベント終了日時（ISO 8601形式：YYYY-MM-DDThh:mm:ss、不明な場合はnull）
4. location: 開催場所（読み取れない場合はnull）
5. organizer: 主催団体（読み取れない場合はnull）
6. target_audience: 対象者（読み取れない場合はnull）
7. summary: イベント内容の短い要約（100文字程度、読み取れない場合はnull）
8. tags: イベント内容に関連するタグ（例: #講演会, #音楽, #スポーツ）を配列形式で（推測できない場合は空配列）

# 注意事項
- 画像から明確に読み取れない情報は必ずnullを設定してください。
- 日付や時間の情報は可能な限り正確に抽出してください。年が記載されていない場合は2025年と仮定してください。
- JSONはUTF-8でエンコードし、日本語文字列はエスケープしないでください。
- 今日の日付は2025年6月19日です。
- 画像が不鮮明で読み取れない場合は、該当項目をnullにしてください。

# 出力形式
{
  "event_name": "イベント名またはnull",
  "event_date_start": "YYYY-MM-DDThh:mm:ssまたはnull",
  "event_date_end": "YYYY-MM-DDThh:mm:ssまたはnull",
  "location": "開催場所またはnull",
  "organizer": "主催団体またはnull",
  "target_audience": "対象者またはnull",
  "description": "イベント内容の短い要約またはnull",
  "source_type": "image",
  "source_data": "画像ファイルパス",
  "tags": ["#タグ1", "#タグ2", ...] または []
}

JSONデータのみを出力してください。説明文やマークダウン記法は使用しないでください。
"""

    try:
        # モデルをロード
        model = genai.GenerativeModel(model_name)
        
        # 画像とプロンプトを送信
        response = model.generate_content([prompt, image])
        
        # レスポンスから JSON を抽出
        json_str = response.text
        
        # JSON部分のみを抽出（マークダウンのコードブロックが含まれている可能性があるため）
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        
        # JSONをパース
        event_data = json.loads(json_str)
        
        # source_dataを画像パスに設定
        event_data["source_type"] = "image"
        event_data["source_data"] = image_path
        
        return event_data
        
    except Exception as e:
        print(f"イベント情報の抽出に失敗しました: {e}")
        # 基本的な情報を返す
        return {
            "event_name": None,
            "event_date_start": None,
            "event_date_end": None,
            "location": None,
            "organizer": None,
            "target_audience": None,
            "summary": None,
            "source_type": "image",
            "source_data": image_path,
            "tags": [],
            "error": str(e)
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
    # 画像ファイルパスを指定
    image_path = "event_flyer.jpg"  # ここに解析したいイベントチラシ画像のパスを指定
    output_file = "event_data_from_image.json"  # 出力ファイル名
    
    try:
        print(f"画像からイベント情報を抽出しています: {image_path}")
        
        # 画像を読み込み
        image = load_image(image_path)
        
        # 画像からイベント情報を抽出
        event_data = extract_event_info_from_image(image, image_path)
        
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
