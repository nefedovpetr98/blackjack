"""
Тренажёр по блэкджеку: базовая стратегия + счёт карт Hi-Lo.

Правила стола: 6 колод, дилер стоит на мягких 17 (S17),
удвоение после сплита разрешено (DAS), сдача (surrender) и страховка не предлагаются.
Блэкджек платит 3:2. Новая колода (шуз) замешивается после ~75% сыгранных карт.

Как играть:
  1. Программа раздаёт карты. На каждом ходу выбираешь действие:
       h / в - взять карту      s / с - стоп
       d / у - удвоить          p / р - разделить (сплит)
     Программа сразу говорит, совпало ли действие с базовой стратегией.
  2. После раунда программа спрашивает текущий бегущий счёт (running count).
     Считай все открытые карты, включая закрытую карту дилера, когда её откроют.
  3. Каждые несколько раундов программа ещё спрашивает истинный счёт (true count).
  q / й - выйти и посмотреть статистику.

Запуск:  python3 blackjack_trainer.py
"""

import random

# ---------- Карты и шуз ----------

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]

NUM_DECKS = 6
PENETRATION = 0.75        # какую долю шуза сдаём до перемешивания
TRUE_COUNT_EVERY = 3      # как часто спрашивать истинный счёт (в раундах)
BET = 10                  # размер ставки в фишках


def card_value(card):
    """Очки карты: туз = 11 (потом может стать 1), картинки = 10."""
    rank = card[:-1]
    if rank == "A":
        return 11
    if rank in ("J", "Q", "K"):
        return 10
    return int(rank)


def hilo_value(card):
    """Вес карты по системе Hi-Lo: 2-6 = +1, 7-9 = 0, 10-A = -1."""
    value = card_value(card)
    if value <= 6:
        return 1
    if value >= 10:
        return -1
    return 0


class Shoe:
    def __init__(self, decks=NUM_DECKS):
        self.decks = decks
        self.shuffle()

    def shuffle(self):
        self.cards = [rank + suit for rank in RANKS for suit in SUITS] * self.decks
        random.shuffle(self.cards)
        self.running_count = 0    # настоящий счёт, его знает только программа
        self.dealt = 0

    def draw(self, visible=True):
        card = self.cards.pop()
        self.dealt += 1
        if visible:
            self.reveal(card)
        return card

    def reveal(self, card):
        """Карта стала видна игроку: учитываем её в счёте."""
        self.running_count += hilo_value(card)

    def decks_left(self):
        return len(self.cards) / 52

    def true_count(self):
        return self.running_count / self.decks_left()

    def needs_shuffle(self):
        return self.dealt >= self.decks * 52 * PENETRATION


# ---------- Руки ----------

def hand_total(cards):
    """Возвращает (сумма очков, мягкая ли рука)."""
    total = sum(card_value(c) for c in cards)
    aces = sum(1 for c in cards if c.startswith("A"))
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total, aces > 0


def is_blackjack(cards):
    return len(cards) == 2 and hand_total(cards)[0] == 21


def show(cards):
    return " ".join(cards)


# ---------- Базовая стратегия (6 колод, S17, DAS) ----------
# Буквы: H - взять, S - стоп, D - удвоить (иначе взять),
#        Ds - удвоить (иначе стоп), P - сплит.

def basic_strategy(cards, dealer_card, can_double, can_split):
    up = card_value(dealer_card)        # 2..11 (11 = туз)
    total, soft = hand_total(cards)

    # Пары
    if can_split and len(cards) == 2 and card_value(cards[0]) == card_value(cards[1]):
        pair = card_value(cards[0])
        split = {
            11: True,
            10: False,
            9: up in (2, 3, 4, 5, 6, 8, 9),
            8: True,
            7: up <= 7,
            6: up <= 6,
            5: False,
            4: up in (5, 6),
            3: up <= 7,
            2: up <= 7,
        }[pair]
        if split:
            return "P"

    if soft and total <= 21:
        if total >= 19:
            action = "S"
        elif total == 18:
            action = "Ds" if 3 <= up <= 6 else ("S" if up in (2, 7, 8) else "H")
        elif total == 17:
            action = "D" if 3 <= up <= 6 else "H"
        elif total in (15, 16):
            action = "D" if 4 <= up <= 6 else "H"
        else:  # 13, 14
            action = "D" if up in (5, 6) else "H"
    else:
        if total >= 17:
            action = "S"
        elif total >= 13:
            action = "S" if up <= 6 else "H"
        elif total == 12:
            action = "S" if 4 <= up <= 6 else "H"
        elif total == 11:
            action = "D" if up <= 10 else "H"
        elif total == 10:
            action = "D" if up <= 9 else "H"
        elif total == 9:
            action = "D" if 3 <= up <= 6 else "H"
        else:
            action = "H"

    # Если удвоить нельзя (уже взял карту), удвоение заменяется
    if action == "D":
        return "D" if can_double else "H"
    if action == "Ds":
        return "D" if can_double else "S"
    return action


ACTION_NAMES = {"H": "взять", "S": "стоп", "D": "удвоить", "P": "сплит"}
INPUT_KEYS = {
    "h": "H", "в": "H",
    "s": "S", "с": "S",
    "d": "D", "у": "D",
    "p": "P", "р": "P",
}


# ---------- Статистика ----------

class Stats:
    def __init__(self):
        self.decisions = 0
        self.correct_decisions = 0
        self.rc_asked = 0
        self.rc_correct = 0
        self.tc_asked = 0
        self.tc_correct = 0
        self.rounds = 0
        self.bankroll = 0

    def report(self):
        def pct(a, b):
            return f"{a}/{b} ({100 * a // b}%)" if b else "—"
        print("\n========== Статистика ==========")
        print(f"Сыграно раундов:          {self.rounds}")
        print(f"Решения по стратегии:     {pct(self.correct_decisions, self.decisions)}")
        print(f"Бегущий счёт верно:       {pct(self.rc_correct, self.rc_asked)}")
        print(f"Истинный счёт верно:      {pct(self.tc_correct, self.tc_asked)}")
        print(f"Выигрыш/проигрыш:         {self.bankroll:+} фишек")
        print("================================\n")


class Quit(Exception):
    pass


def ask(prompt):
    answer = input(prompt).strip().lower()
    if answer in ("q", "й"):
        raise Quit
    return answer


def ask_number(prompt):
    while True:
        answer = ask(prompt).replace(",", ".")
        try:
            return float(answer)
        except ValueError:
            print("  Введи число (например 3, -2 или 1.5).")


# ---------- Один раунд ----------

def play_hand(cards, dealer_up, shoe, stats, hands, from_split_aces=False):
    """Игрок принимает решения по одной руке. Возвращает (карты, ставка)."""
    bet = BET
    if from_split_aces:
        # После сплита тузов даётся только одна карта
        print(f"  Рука: {show(cards)} (после сплита тузов больше карт не дают)")
        return cards, bet

    while True:
        total, soft = hand_total(cards)
        if total >= 21:
            return cards, bet

        can_double = len(cards) == 2
        can_split = (len(cards) == 2 and card_value(cards[0]) == card_value(cards[1])
                     and len(hands) < 4)

        options = "[h/в] взять, [s/с] стоп"
        if can_double:
            options += ", [d/у] удвоить"
        if can_split:
            options += ", [p/р] сплит"
        label = "мягкие " if soft else ""
        print(f"\n  Твоя рука: {show(cards)}  ({label}{total})   Дилер: {dealer_up}")

        while True:
            choice = INPUT_KEYS.get(ask(f"  Действие ({options}): "))
            if choice is None:
                print("  Не понял. Попробуй ещё раз.")
            elif choice == "D" and not can_double:
                print("  Удвоить можно только на первых двух картах.")
            elif choice == "P" and not can_split:
                print("  Сплит здесь невозможен.")
            else:
                break

        correct = basic_strategy(cards, dealer_up, can_double, can_split)
        stats.decisions += 1
        if choice == correct:
            stats.correct_decisions += 1
            print(f"  ✅ Молодец! «{ACTION_NAMES[choice]}» - верно по базовой стратегии.")
        else:
            print(f"  ❌ По базовой стратегии здесь «{ACTION_NAMES[correct]}», "
                  f"а ты выбрал «{ACTION_NAMES[choice]}». Играем твой вариант.")

        if choice == "S":
            return cards, bet
        if choice == "H":
            cards.append(shoe.draw())
            print(f"  Получил: {cards[-1]}")
        elif choice == "D":
            bet *= 2
            cards.append(shoe.draw())
            print(f"  Удвоил, получил: {cards[-1]}  → {hand_total(cards)[0]}")
            return cards, bet
        elif choice == "P":
            # Вторую карту уводим в новую руку; сыграем её позже
            second = [cards.pop()]
            hands.append(second)
            cards.append(shoe.draw())
            print(f"  Разделил. Первая рука: {show(cards)}")
            if cards[0].startswith("A"):
                return play_hand(cards, dealer_up, shoe, stats, hands, from_split_aces=True)


def play_round(shoe, stats):
    stats.rounds += 1
    print(f"\n────────── Раунд {stats.rounds} ──────────  "
          f"(осталось колод: {shoe.decks_left():.1f})")

    player = [shoe.draw(), shoe.draw()]
    dealer_up = shoe.draw()
    dealer_hole = shoe.draw(visible=False)   # закрытую карту пока не считаем

    print(f"Дилер: {dealer_up} [?]")
    print(f"Ты:    {show(player)}")

    # Блэкджеки
    if is_blackjack([dealer_up, dealer_hole]) or is_blackjack(player):
        shoe.reveal(dealer_hole)
        print(f"Дилер открывает: {dealer_up} {dealer_hole}")
        if is_blackjack(player) and is_blackjack([dealer_up, dealer_hole]):
            print("Оба с блэкджеком - ничья.")
        elif is_blackjack(player):
            print("🎉 Блэкджек! Выплата 3:2.")
            stats.bankroll += BET * 3 // 2
        else:
            print("У дилера блэкджек. Ставка проиграна.")
            stats.bankroll -= BET
        return

    # Игрок играет все свои руки (их может стать больше после сплитов)
    hands = [player]
    results = []
    i = 0
    while i < len(hands):
        if len(hands) > 1:
            print(f"\n  --- Рука {i + 1} из {len(hands)} ---")
            if len(hands[i]) == 1:          # рука после сплита ждёт вторую карту
                hands[i].append(shoe.draw())
                print(f"  Добор ко второй руке: {hands[i][-1]}")
        split_aces = len(hands) > 1 and hands[i][0].startswith("A")
        results.append(play_hand(hands[i], dealer_up, shoe, stats, hands,
                                 from_split_aces=split_aces))
        i += 1

    # Дилер открывает карту и добирает до 17 (на мягких 17 стоит)
    shoe.reveal(dealer_hole)
    dealer = [dealer_up, dealer_hole]
    if any(hand_total(cards)[0] <= 21 for cards, _ in results):
        while hand_total(dealer)[0] < 17:
            dealer.append(shoe.draw())
    dealer_total = hand_total(dealer)[0]
    print(f"\nДилер: {show(dealer)}  ({dealer_total})")

    for n, (cards, bet) in enumerate(results, 1):
        total = hand_total(cards)[0]
        prefix = f"Рука {n}: " if len(results) > 1 else ""
        if total > 21:
            print(f"{prefix}{show(cards)} ({total}) - перебор, -{bet}")
            stats.bankroll -= bet
        elif dealer_total > 21 or total > dealer_total:
            print(f"{prefix}{show(cards)} ({total}) - победа, +{bet}")
            stats.bankroll += bet
        elif total == dealer_total:
            print(f"{prefix}{show(cards)} ({total}) - ничья")
        else:
            print(f"{prefix}{show(cards)} ({total}) - проигрыш, -{bet}")
            stats.bankroll -= bet


def check_count(shoe, stats):
    answer = ask_number("\nКакой сейчас бегущий счёт (running count)? ")
    stats.rc_asked += 1
    if int(answer) == shoe.running_count:
        stats.rc_correct += 1
        print(f"  ✅ Молодец, счёт верный: {shoe.running_count:+d}")
    else:
        print(f"  ❌ Правильный бегущий счёт: {shoe.running_count:+d} (ты сказал {int(answer):+d})")

    if stats.rounds % TRUE_COUNT_EVERY == 0:
        exact = shoe.true_count()
        answer = ask_number(f"Осталось колод ≈ {shoe.decks_left():.1f}. "
                            "Какой истинный счёт (true count)? ")
        stats.tc_asked += 1
        if abs(answer - exact) <= 0.5:
            stats.tc_correct += 1
            print(f"  ✅ Верно! Истинный счёт ≈ {exact:+.1f}")
        else:
            print(f"  ❌ Истинный счёт ≈ {exact:+.1f} "
                  f"(бегущий {shoe.running_count:+d} / {shoe.decks_left():.1f} колод)")


def main():
    print(__doc__)
    shoe = Shoe()
    stats = Stats()
    try:
        while True:
            if shoe.needs_shuffle():
                print("\n🔀 Шуз перемешан. Счёт начинается заново с 0.")
                shoe.shuffle()
            play_round(shoe, stats)
            check_count(shoe, stats)
            ask("\nEnter - следующий раунд, q - выход: ")
    except (Quit, EOFError, KeyboardInterrupt):
        pass
    stats.report()


if __name__ == "__main__":
    main()
