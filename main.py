import asyncio
import random
import threading
import time

import flet as ft


PALETTE = [
    ("Vermelho", ft.Colors.RED_400),
    ("Azul", ft.Colors.BLUE_400),
    ("Verde", ft.Colors.GREEN_400),
    ("Amarelo", ft.Colors.YELLOW_600),
    ("Roxo", ft.Colors.PURPLE_400),
    ("Ciano", ft.Colors.CYAN_400),
    ("Rosa", ft.Colors.PINK_400),
    ("Laranja", ft.Colors.ORANGE_400),
]

MAX_ORBS = 8
BASE_INTERVAL = 2.2
MIN_INTERVAL = 0.7
HITS_PER_LEVEL = 8
VICTORY_LEVEL = 8
MAX_STABILITY = 100


def main(page: ft.Page):
  
    page.theme_mode = ft.ThemeMode.DARK
    
    page.window.width = 390
    page.window.height = 844
    page.window.min_width = 320
    page.window.min_height = 560
    page.window.resizable = True
    page.bgcolor = ft.Colors.GREY_900
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

   
    lock = threading.Lock()

    state = {
        "running": False,
        "paused": False,
        "game_over": False,
        "victory": False,
        "score": 0,
        "combo": 0,
        "level": 1,
        "stability": MAX_STABILITY,
        "hits_this_level": 0,
        "tick_done": False,
        "tick_start": 0.0,
        "pause_started": 0.0,
        "interval": BASE_INTERVAL,
    }

    orbs = [{"active": False} for _ in range(MAX_ORBS)]
   
    task_holder = {"generation": 0}

    
    title_text = ft.Text(
        "NEXUS: RESSONÂNCIA",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.CYAN_200,
    )

    level_text = ft.Text(
        "Nível 1",
        size=14,
        color=ft.Colors.WHITE,
        weight=ft.FontWeight.W_600,
    )

    score_text = ft.Text(
        "Pontos: 0",
        size=14,
        color=ft.Colors.AMBER_300,
        weight=ft.FontWeight.W_600,
    )

    combo_text = ft.Text(
        "Combo: 0x",
        size=14,
        color=ft.Colors.PINK_200,
        weight=ft.FontWeight.W_600,
    )

    stability_label = ft.Text(
        "Estabilidade do Núcleo",
        size=11,
        color=ft.Colors.GREY_400,
    )

    stability_bar = ft.ProgressBar(
        value=1.0,
        width=340,
        height=16,
        border_radius=8,
        color=ft.Colors.GREEN_400,
        bgcolor=ft.Colors.GREY_800,
    )


    target_circle = ft.Container(
        width=40,
        height=40,
        border_radius=20,
        bgcolor=ft.Colors.GREY_700,
        border=ft.Border(
            left=ft.BorderSide(2, ft.Colors.WHITE_24),
            top=ft.BorderSide(2, ft.Colors.WHITE_24),
            right=ft.BorderSide(2, ft.Colors.WHITE_24),
            bottom=ft.BorderSide(2, ft.Colors.WHITE_24),
        ),
        animate=ft.Animation(250, ft.AnimationCurve.EASE_OUT),
    )

    target_label = ft.Text(
        "ALVO: --",
        size=16,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE,
    )

    round_timer_bar = ft.ProgressBar(
        value=1.0,
        width=340,
        height=6,
        border_radius=4,
        color=ft.Colors.CYAN_300,
        bgcolor=ft.Colors.GREY_800,
    )

    feedback_text = ft.Text(
        "",
        size=15,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE,
        text_align=ft.TextAlign.CENTER,
    )

   
    pause_button = ft.OutlinedButton(
        "PAUSAR",
        icon=ft.Icons.PAUSE_ROUNDED,
    )

    exit_button = ft.OutlinedButton(
        "SAIR",
        icon=ft.Icons.EXIT_TO_APP_ROUNDED,
    )

  
    def make_orb_container(idx: int) -> ft.Container:
        return ft.Container(
            width=64,
            height=64,
            border_radius=32,
            bgcolor=ft.Colors.GREY_800,
            border=ft.Border(
                left=ft.BorderSide(2, ft.Colors.GREY_600),
                top=ft.BorderSide(2, ft.Colors.GREY_600),
                right=ft.BorderSide(2, ft.Colors.GREY_600),
                bottom=ft.BorderSide(2, ft.Colors.GREY_600),
            ),
            content=None,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_click=lambda e, i=idx: handle_orb_tap(i),
        )

    orb_containers = [make_orb_container(i) for i in range(MAX_ORBS)]

    orb_row_1 = ft.Row(
        orb_containers[0:4],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
    )

    orb_row_2 = ft.Row(
        orb_containers[4:8],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
    )

   
    def update_status_ui(feedback: str = ""):
        with lock:
            score = state["score"]
            combo = state["combo"]
            level = state["level"]
            stability = state["stability"]

        level_text.value = f"Nível {level}"
        score_text.value = f"Pontos: {score}"
        combo_text.value = f"Combo: {combo}x"

        ratio = max(0.0, min(1.0, stability / MAX_STABILITY))
        stability_bar.value = ratio

        if ratio > 0.5:
            stability_bar.color = ft.Colors.GREEN_400
        elif ratio > 0.25:
            stability_bar.color = ft.Colors.AMBER_400
        else:
            stability_bar.color = ft.Colors.RED_400

        feedback_text.value = feedback
        page.update()

    def apply_orbs_to_ui(target_name: str, target_color: str):
        for i, orb in enumerate(orbs):
            c = orb_containers[i]

            if not orb.get("active"):
                c.visible = False
                c.content = None
                continue

            c.visible = True
            c.bgcolor = orb["color"]
            c.scale = 1.0

            icon = None
            border_color = ft.Colors.GREY_600

            if orb.get("is_decoy"):
                icon = ft.Icon(
                    ft.Icons.WARNING_AMBER_ROUNDED,
                    color=ft.Colors.WHITE,
                    size=26,
                )
                border_color = ft.Colors.RED_300

            elif orb.get("is_bonus"):
                icon = ft.Icon(
                    ft.Icons.STAR_ROUNDED,
                    color=ft.Colors.WHITE,
                    size=26,
                )
                border_color = ft.Colors.AMBER_300

            c.content = icon
            c.border = ft.Border(
                left=ft.BorderSide(2, border_color),
                top=ft.BorderSide(2, border_color),
                right=ft.BorderSide(2, border_color),
                bottom=ft.BorderSide(2, border_color),
            )

        target_circle.bgcolor = target_color
        target_label.value = f"ALVO: {target_name}"
        round_timer_bar.value = 1.0
        round_timer_bar.color = ft.Colors.CYAN_300
        feedback_text.value = ""
        page.update()

   
    def new_round(interval: float):
        with lock:
            level = state["level"]
            num_orbs = min(4 + level // 2, MAX_ORBS)

            chosen = random.sample(PALETTE, num_orbs)
            target_idx = random.randrange(num_orbs)
            target_name, target_color = chosen[target_idx]

            decoy_idx = None
            if level >= 2 and random.random() < 0.30:
                candidates = [
                    i for i in range(num_orbs)
                    if i != target_idx
                ]
                if candidates:
                    decoy_idx = random.choice(candidates)

            bonus_idx = None
            if random.random() < 0.15:
                candidates = [
                    i for i in range(num_orbs)
                    if i != target_idx and i != decoy_idx
                ]
                if candidates:
                    bonus_idx = random.choice(candidates)

            orbs.clear()

            for i in range(MAX_ORBS):
                if i < num_orbs:
                    name, color = chosen[i]
                    orbs.append(
                        {
                            "active": True,
                            "name": name,
                            "color": color,
                            "is_target": i == target_idx,
                            "is_decoy": i == decoy_idx,
                            "is_bonus": i == bonus_idx,
                        }
                    )
                else:
                    orbs.append({"active": False})

            state["tick_done"] = False
            state["tick_start"] = time.perf_counter()
            state["interval"] = interval

        apply_orbs_to_ui(target_name, target_color)

    def compute_interval() -> float:
        with lock:
            level = state["level"]
        return max(MIN_INTERVAL, BASE_INTERVAL - 0.12 * (level - 1))

    
    end_icon = ft.Icon(
        ft.Icons.EMOJI_EVENTS_ROUNDED,
        color=ft.Colors.AMBER_300,
        size=32,
    )

    end_title = ft.Text(
        "🎉 VITÓRIA!",
        size=22,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.AMBER_300,
    )

    end_message = ft.Text(
        "",
        size=15,
        text_align=ft.TextAlign.CENTER,
    )

    end_reward = ft.Text(
        "",
        size=16,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    end_score = ft.Text(
        "",
        size=15,
        weight=ft.FontWeight.BOLD,
        text_align=ft.TextAlign.CENTER,
    )

    end_level = ft.Text(
        "",
        size=14,
        text_align=ft.TextAlign.CENTER,
    )

    def start_game(e=None):
        # Fecha qualquer tela secundária antes de começar novamente.
        pause_overlay.visible = False
        end_overlay.visible = False

        with lock:
            state.update(
                running=True,
                paused=False,
                game_over=False,
                victory=False,
                score=0,
                combo=0,
                level=1,
                stability=MAX_STABILITY,
                hits_this_level=0,
                tick_done=False,
                tick_start=0.0,
                pause_started=0.0,
                interval=BASE_INTERVAL,
            )
            task_holder["generation"] += 1
            my_generation = task_holder["generation"]

        start_overlay.visible = False
        pause_button.text = "PAUSAR"
        pause_button.icon = ft.Icons.PAUSE_ROUNDED
        update_status_ui("")

        for c in orb_containers:
            c.visible = False
            c.content = None

        page.update()

       
        page.run_task(game_loop, my_generation)

    def reset_to_home(e=None):
        # Invalida a thread atual.
        with lock:
            state["running"] = False
            state["paused"] = False
            state["game_over"] = False
            state["victory"] = False
            task_holder["generation"] += 1

        pause_overlay.visible = False
        end_overlay.visible = False
        start_overlay.visible = True

        for c in orb_containers:
            c.visible = False
            c.content = None

        target_circle.bgcolor = ft.Colors.GREY_700
        target_label.value = "ALVO: --"
        round_timer_bar.value = 1.0
        round_timer_bar.color = ft.Colors.CYAN_300
        pause_button.text = "PAUSAR"
        pause_button.icon = ft.Icons.PAUSE_ROUNDED

        with lock:
            state["score"] = 0
            state["combo"] = 0
            state["level"] = 1
            state["stability"] = MAX_STABILITY
            state["hits_this_level"] = 0

        update_status_ui("")
        page.update()

    
    def toggle_pause(e=None):
        with lock:
            if not state["running"] or state["game_over"] or state["victory"]:
                return

            if not state["paused"]:
                state["paused"] = True
                state["pause_started"] = time.perf_counter()
                paused_now = True
            else:
                pause_duration = time.perf_counter() - state["pause_started"]
                state["tick_start"] += pause_duration
                state["pause_started"] = 0.0
                state["paused"] = False
                paused_now = False

        if paused_now:
            pause_button.text = "CONTINUAR"
            pause_button.icon = ft.Icons.PLAY_ARROW_ROUNDED
            pause_overlay.visible = True
        else:
            pause_button.text = "PAUSAR"
            pause_button.icon = ft.Icons.PAUSE_ROUNDED
            pause_overlay.visible = False

        page.update()

    pause_button.on_click = toggle_pause
    exit_button.on_click = reset_to_home

    
    def handle_orb_tap(idx: int):
        feedback = ""
        game_over_now = False
        victory_now = False

        with lock:
            if (
                not state["running"]
                or state["paused"]
                or state["game_over"]
                or state["victory"]
                or state["tick_done"]
            ):
                return

            if idx >= len(orbs) or not orbs[idx].get("active"):
                return

            orb = orbs[idx]
            elapsed = time.time() - state["tick_start"]

            if orb["is_target"]:
                state["tick_done"] = True
                state["combo"] += 1

                multiplier = 1 + state["combo"] // 5
                points = 10 * multiplier
                fast = elapsed < state["interval"] * 0.35

                if fast:
                    points += 5

                state["score"] += points
                state["stability"] = min(
                    MAX_STABILITY,
                    state["stability"] + 4,
                )
                state["hits_this_level"] += 1

                feedback = f"+{points}  {'PERFEITO!' if fast else 'RESSOOU!'}"

                if state["hits_this_level"] >= HITS_PER_LEVEL:
                    state["hits_this_level"] = 0
                    state["level"] += 1
                    feedback += "  ↑ NÍVEL!"

                if state["level"] >= VICTORY_LEVEL:
                    state["victory"] = True
                    state["running"] = False
                    victory_now = True

            elif orb.get("is_decoy"):
                state["stability"] -= 15
                state["combo"] = 0
                feedback = "ARMADILHA!  -15"

            elif orb.get("is_bonus"):
                state["score"] += 8
                state["stability"] = min(
                    MAX_STABILITY,
                    state["stability"] + 2,
                )
                feedback = "FRAGMENTO BÔNUS!  +8"

            else:
                state["stability"] -= 8
                state["combo"] = 0
                feedback = "COR ERRADA!  -8"

            if state["stability"] <= 0 and not victory_now:
                state["stability"] = 0
                state["game_over"] = True
                state["running"] = False
                game_over_now = True

        update_status_ui(feedback)

        if victory_now:
            show_end_dialog(True)
        elif game_over_now:
            show_end_dialog(False)

    def handle_timeout():
        feedback = ""
        game_over_now = False

        with lock:
            if (
                not state["running"]
                or state["paused"]
                or state["game_over"]
                or state["victory"]
                or state["tick_done"]
            ):
                return

            state["stability"] -= 15
            state["combo"] = 0
            feedback = "TEMPO ESGOTADO!  -15"

            if state["stability"] <= 0:
                state["stability"] = 0
                state["game_over"] = True
                state["running"] = False
                game_over_now = True

        update_status_ui(feedback)

        if game_over_now:
            show_end_dialog(False)


    async def game_loop(my_generation: int):
        """Loop principal assíncrono do jogo.

        Usar asyncio em vez de uma thread deixa o cronômetro e as atualizações
        da interface sincronizados com o Flet em desktop e mobile.
        """
        while True:
            with lock:
                if (
                    task_holder["generation"] != my_generation
                    or not state["running"]
                ):
                    return

                paused = state["paused"]

            if paused:
                await asyncio.sleep(0.05)
                continue

            interval = compute_interval()
            new_round(interval)

            while True:
                with lock:
                    if (
                        task_holder["generation"] != my_generation
                        or not state["running"]
                    ):
                        return

                    paused = state["paused"]
                    done = state["tick_done"]
                    tick_start = state["tick_start"]
                    current_interval = state["interval"]

                # Durante a pausa, não avançamos o relógio. Ao voltar,
                # toggle_pause ajusta tick_start pelo tempo que ficou pausado.
                if paused:
                    await asyncio.sleep(0.05)
                    continue

                elapsed = time.perf_counter() - tick_start

                if done:
                    break

                if elapsed >= current_interval:
                    handle_timeout()
                    break

                remaining_ratio = max(
                    0.0,
                    min(1.0, 1 - (elapsed / current_interval)),
                )

                round_timer_bar.value = remaining_ratio

                if remaining_ratio < 0.25:
                    round_timer_bar.color = ft.Colors.RED_400
                else:
                    round_timer_bar.color = ft.Colors.CYAN_300

                # Como estamos dentro da tarefa do Flet, a atualização é feita
                # de forma segura no mesmo event loop da interface.
                page.update()

                await asyncio.sleep(0.05)

            with lock:
                if (
                    task_holder["generation"] != my_generation
                    or state["game_over"]
                    or state["victory"]
                    or not state["running"]
                ):
                    return

                was_done = state["tick_done"]

            if was_done:
                await asyncio.sleep(0.25)

  
    def show_end_dialog(win=False):
        with lock:
            reward = 100 if win else 0

            if win:
                state["score"] += reward

            final_score = state["score"]
            final_level = state["level"]

        if win:
            end_icon.name = ft.Icons.EMOJI_EVENTS_ROUNDED
            end_icon.color = ft.Colors.AMBER_300
            end_title.value = "🎉 VITÓRIA!"
            end_title.color = ft.Colors.AMBER_300
            end_message.value = (
                "Parabéns! Você estabilizou o Nexus e alcançou o Nível 8."
            )
            end_reward.value = f"🏆 PRÊMIO: +{reward} pontos!"
            end_reward.color = ft.Colors.AMBER_300
        else:
            end_icon.name = ft.Icons.HEART_BROKEN_ROUNDED
            end_icon.color = ft.Colors.RED_300
            end_title.value = "💥 VOCÊ PERDEU!"
            end_title.color = ft.Colors.RED_300
            end_message.value = (
                "O Núcleo colapsou! Sua estabilidade chegou a zero."
            )
            end_reward.value = (
                "💡 DICA: toque apenas na cor-alvo e evite as armadilhas."
            )
            end_reward.color = ft.Colors.CYAN_200

        end_score.value = f"Pontuação final: {final_score}"
        end_level.value = f"Nível alcançado: {final_level}"

        pause_overlay.visible = False
        end_overlay.visible = True
        page.update()

   
    def close_end_and_restart(e=None):
        # Fecha a tela de resultado ANTES de iniciar uma nova partida.
        end_overlay.visible = False
        page.update()
        start_game()

    end_overlay = ft.Container(
        visible=False,
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor=ft.Colors.with_opacity(0.94, ft.Colors.GREY_900),
        content=ft.Container(
            width=360,
            padding=22,
            border_radius=20,
            bgcolor=ft.Colors.GREY_800,
            border=ft.Border(
                left=ft.BorderSide(1, ft.Colors.CYAN_700),
                top=ft.BorderSide(1, ft.Colors.CYAN_700),
                right=ft.BorderSide(1, ft.Colors.CYAN_700),
                bottom=ft.BorderSide(1, ft.Colors.CYAN_700),
            ),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
                controls=[
                    ft.Row(
                        controls=[end_icon, end_title],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    end_message,
                    ft.Divider(),
                    end_reward,
                    end_score,
                    end_level,
                    ft.Container(height=4),
                    ft.FilledButton(
                        "JOGAR NOVAMENTE",
                        icon=ft.Icons.REPLAY_ROUNDED,
                        on_click=close_end_and_restart,
                    ),
                    ft.OutlinedButton(
                        "VOLTAR AO INÍCIO",
                        icon=ft.Icons.HOME_ROUNDED,
                        on_click=reset_to_home,
                    ),
                ],
            ),
        ),
    )


    pause_overlay = ft.Container(
        visible=False,
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor=ft.Colors.with_opacity(0.88, ft.Colors.GREY_900),
        content=ft.Container(
            width=340,
            padding=22,
            border_radius=18,
            bgcolor=ft.Colors.GREY_800,
            border=ft.Border(
                left=ft.BorderSide(1, ft.Colors.CYAN_700),
                top=ft.BorderSide(1, ft.Colors.CYAN_700),
                right=ft.BorderSide(1, ft.Colors.CYAN_700),
                bottom=ft.BorderSide(1, ft.Colors.CYAN_700),
            ),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=14,
                controls=[
                    ft.Icon(
                        ft.Icons.PAUSE_CIRCLE_FILLED_ROUNDED,
                        size=58,
                        color=ft.Colors.CYAN_200,
                    ),
                    ft.Text(
                        "JOGO PAUSADO",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                    ),
                    ft.Text(
                        "O tempo está parado.\nContinue quando quiser.",
                        size=14,
                        color=ft.Colors.GREY_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        "CONTINUAR",
                        icon=ft.Icons.PLAY_ARROW_ROUNDED,
                        on_click=toggle_pause,
                    ),
                    ft.OutlinedButton(
                        "SAIR DO JOGO",
                        icon=ft.Icons.EXIT_TO_APP_ROUNDED,
                        on_click=reset_to_home,
                    ),
                ],
            ),
        ),
    )

   
    start_overlay = ft.Container(
        visible=True,
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor=ft.Colors.with_opacity(0.94, ft.Colors.GREY_900),
        content=ft.Container(
            width=350,
            padding=22,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                tight=True,
                controls=[
                    ft.Icon(
                        ft.Icons.HUB_ROUNDED,
                        size=54,
                        color=ft.Colors.CYAN_200,
                    ),
                    ft.Text(
                        "NEXUS: RESSONÂNCIA",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Toque na esfera que ressoa com a COR-ALVO antes do tempo acabar.\n\n"
                        "⚠  Esferas com aviso são armadilhas — evite-as.\n"
                        "⭐  Fragmentos dourados dão bônus — capture-os!\n\n"
                        "Sobreviva e alcance o Nível 8 para vencer.",
                        size=13,
                        color=ft.Colors.GREY_300,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.FilledButton(
                        "INICIAR JOGO",
                        icon=ft.Icons.PLAY_ARROW_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.CYAN_700,
                            color=ft.Colors.WHITE,
                        ),
                        on_click=start_game,
                    ),
                ],
            ),
        ),
    )

   
    stats_row = ft.Row(
        [level_text, score_text, combo_text],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        width=340,
    )

    feedback_box = ft.Container(
        height=30,
        width=340,
        alignment=ft.Alignment(0, 0),
        content=feedback_text,
    )

    game_content = ft.Container(
        expand=True,
        padding=ft.Padding(12, 12, 12, 12),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                title_text,
                stats_row,
                ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    controls=[stability_label, stability_bar],
                ),
                ft.Row(
                    [target_circle, target_label],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=12,
                ),
                round_timer_bar,
                feedback_box,
                ft.Row(
                    [pause_button, exit_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=14,
                ),
                ft.Text(
                    "Use o mouse para clicar nas esferas • PAUSAR interrompe o tempo",
                    size=11,
                    color=ft.Colors.GREY_500,
                    text_align=ft.TextAlign.CENTER,
                ),
                orb_row_1,
                orb_row_2,
            ],
        ),
    )

   
    def update_responsive_layout(e=None):
        try:
            width = float(page.width or 390)
            height = float(page.height or 844)
        except Exception:
            width, height = 390, 844

        # Largura útil, sem deixar os controles encostarem nas bordas.
        content_width = max(280, min(width - 24, 720))

        # As barras e a linha de status acompanham a largura da tela.
        stability_bar.width = content_width
        round_timer_bar.width = content_width
        stats_row.width = content_width
        feedback_box.width = content_width

        # Esferas: quatro por linha tanto no celular quanto no computador.
        orb_size = max(52, min(88, (content_width - 24) / 4))
        orb_radius = orb_size / 2
        orb_spacing = max(6, min(18, (content_width - orb_size * 4) / 3))

        for c in orb_containers:
            c.width = orb_size
            c.height = orb_size
            c.border_radius = orb_radius

        orb_row_1.spacing = orb_spacing
        orb_row_2.spacing = orb_spacing

        # Cards de início, pausa e resultado nunca ultrapassam a tela.
        start_width = max(280, min(500, width - 28))
        pause_width = max(280, min(420, width - 28))
        end_width = max(280, min(460, width - 28))

        start_overlay.content.width = start_width
        pause_overlay.content.width = pause_width
        end_overlay.content.width = end_width

        # Em telas pequenas, reduzimos um pouco o espaçamento vertical.
        compact = height < 700 or width < 360
        game_content.padding = ft.Padding(10 if compact else 16, 8 if compact else 16, 10 if compact else 16, 8 if compact else 16)

        page.update()

    page.on_resize = update_responsive_layout

   
    page.add(
        ft.Stack(expand=True,controls=[game_content,start_overlay,pause_overlay,end_overlay,
            ],
        )
    )

    # Garante o estado inicial dos controles.
    for c in orb_containers:
        c.visible = False

    update_responsive_layout()


if __name__ == "__main__":
    ft.run(main)
