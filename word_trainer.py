import json
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


DATA_FILE = Path("words.json")


@dataclass
class Word:
    english: str
    chinese: str
    level: int = 1  # 1-5, higher means more familiar
    attempts: int = 0
    correct: int = 0


def load_words() -> List[Word]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [Word(**item) for item in data]


def save_words(words: List[Word]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump([asdict(w) for w in words], f, ensure_ascii=False, indent=2)


def add_word(words: List[Word]) -> None:
    english = input("英文: ").strip()
    chinese = input("中文释义: ").strip()

    if not english or not chinese:
        print("输入不能为空。")
        return

    for w in words:
        if w.english.lower() == english.lower():
            print("该单词已存在，已更新释义。")
            w.chinese = chinese
            save_words(words)
            return

    words.append(Word(english=english, chinese=chinese))
    save_words(words)
    print("添加成功。")


def show_progress(words: List[Word]) -> None:
    if not words:
        print("词库为空，请先添加单词。")
        return

    total = len(words)
    avg_level = sum(w.level for w in words) / total
    total_attempts = sum(w.attempts for w in words)
    total_correct = sum(w.correct for w in words)
    accuracy = (total_correct / total_attempts * 100) if total_attempts else 0

    print(f"总词数: {total}")
    print(f"平均熟悉度(1-5): {avg_level:.2f}")
    print(f"总正确率: {accuracy:.1f}%")

    print("\n掌握较弱(熟悉度<=2)的单词:")
    weak_words = [w for w in words if w.level <= 2]
    if not weak_words:
        print("无，继续保持！")
    else:
        for w in weak_words[:10]:
            print(f"- {w.english} -> {w.chinese} (熟悉度 {w.level})")


def review(words: List[Word]) -> None:
    if not words:
        print("词库为空，请先添加单词。")
        return

    # Weighted sampling: lower level gets higher probability
    weights = [max(1, 6 - w.level) for w in words]
    target = random.choices(words, weights=weights, k=1)[0]

    print(f"\n请写出这个中文对应的英文：{target.chinese}")
    answer = input("你的答案: ").strip()

    target.attempts += 1
    if answer.lower() == target.english.lower():
        target.correct += 1
        target.level = min(5, target.level + 1)
        print("回答正确！熟悉度 +1")
    else:
        target.level = max(1, target.level - 1)
        print(f"回答不正确。正确答案是: {target.english}")
        print("熟悉度 -1")

    save_words(words)


def list_words(words: List[Word]) -> None:
    if not words:
        print("词库为空。")
        return
    print("\n当前词库：")
    for i, w in enumerate(words, start=1):
        acc = (w.correct / w.attempts * 100) if w.attempts else 0
        print(
            f"{i}. {w.english} -> {w.chinese} | 熟悉度:{w.level} | 练习:{w.attempts} | 正确率:{acc:.0f}%"
        )


def main() -> None:
    words = load_words()
    menu = """
=== 背单词小程序 ===
1. 添加单词
2. 开始抽查
3. 查看词库
4. 查看学习进度
0. 退出
"""

    while True:
        print(menu)
        choice = input("请选择: ").strip()

        if choice == "1":
            add_word(words)
        elif choice == "2":
            review(words)
        elif choice == "3":
            list_words(words)
        elif choice == "4":
            show_progress(words)
        elif choice == "0":
            print("已退出，继续加油！")
            break
        else:
            print("无效选项，请重新输入。")


if __name__ == "__main__":
    main()
