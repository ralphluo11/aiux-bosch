from pathlib import Path

from ai_ux_core.knowledge import load_knowledge_cards
from ai_ux_core.models import GuideQuestion, ResearchBrief
from ai_ux_core.orchestrator import InterviewOrchestrator


def main() -> None:
    project_root = Path(__file__).parent
    cards = load_knowledge_cards(project_root / "knowledge" / "fridge_cards.yaml")
    brief = ResearchBrief(
        goal="了解用户对冷藏室温度分布的真实体验",
        target_user="家庭冰箱主要使用者",
        research_questions=["用户在什么情境下感受到温度不均？"],
        product_scope="refrigerator",
    )
    guide = [
        GuideQuestion(
            text="最近使用冰箱时，有没有让你困扰的温度问题？",
            intent="发现温度相关问题",
            research_question_id="rq_1",
            order=1,
            max_followups=1,
        ),
        GuideQuestion(
            text="这个问题对你保存食物造成了什么影响？",
            intent="理解结果和严重性",
            research_question_id="rq_1",
            order=2,
            max_followups=0,
        ),
    ]

    engine = InterviewOrchestrator(brief, guide, cards)
    session = engine.start()

    print("Q:", session.current_question)
    first = engine.submit_answer(session, "后面的菜经常冻住，但是门边的饮料又不够冷。")
    print("Decision:", first.model_dump(mode="json"))
    print("Q:", session.current_question)

    second = engine.submit_answer(session, "通常是靠近后壁的位置，塞得比较满的时候更明显。")
    print("Decision:", second.model_dump(mode="json"))
    print("Q:", session.current_question)

    third = engine.submit_answer(session, "有些蔬菜会坏掉，只能换一个位置存放。")
    print("Decision:", third.model_dump(mode="json"))
    print("Session status:", session.status)


if __name__ == "__main__":
    main()

