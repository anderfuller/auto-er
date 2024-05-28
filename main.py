import flet as ft
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import yaml

# FIXME: - uhhhhhhhhhhhhhhhhhh
# RIGHT! need to add in funny calculations for funny maths
# i.e. total charge passed, time expected, etc
# not for analysis purposes but just kinda for funsies n such


def main(page):
    page.theme_mode = ft.ThemeMode.LIGHT
    page.title = "Auto ER"
    page.window_maximized = True
    page.theme = ft.Theme(use_material3=True)
    page.vertical_alginment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    async def rail_change(rail_dest):
        index = rail_dest.data
        match index:
            case "0":
                main_context.content = quick_view_container
                await main_context.update_async()

            case "1":
                main_context.content = run_summary_container
                await main_context.update_async()

            case "2":
                main_context.content = sweeps_conainer
                await main_context.update_async()

            case "3":
                main_context.content = settings_container
                await main_context.update_async()

    # Quick View container
    quick_view_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Quick View",
                        theme_style=ft.TextThemeStyle.TITLE_LARGE,
                        text_align=ft.TextAlign.CENTER,
                        expand=True,
                    ),
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True, bgcolor=ft.colors.YELLOW),
            ],
            expand=True,
            alignment=ft.alignment.center,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )

    # Run summary page
    run_summary_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Run Summary",
                        theme_style=ft.TextThemeStyle.TITLE_LARGE,
                        text_align=ft.TextAlign.CENTER,
                        expand=True,
                    ),
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True, bgcolor=ft.colors.RED),
            ],
            expand=True,
            alignment=ft.alignment.center,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )

    # Sweeps Page
    sweeps_conainer = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Sweeps",
                        theme_style=ft.TextThemeStyle.TITLE_LARGE,
                        text_align=ft.TextAlign.CENTER,
                        expand=True,
                    ),
                    alignment=ft.alignment.center,
                ),
                ft.Container(expand=True, bgcolor=ft.colors.BLUE),
            ],
            expand=True,
            alignment=ft.alignment.center,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )

    # Settings Fields
    refining_period_field = ft.TextField(label="Refining Period")
    back_emf_period_field = ft.TextField(label="Back Emf Period")
    sweep_duration_field = ft.TextField(label="Sweep Duration")
    sample_period_field = ft.TextField(label="Sample Period")
    step_duration_field = ft.TextField(label="Step Duration")
    step_magnitude_field = ft.TextField(label="Step Magnitude")
    sweep_limit_field = ft.TextField(label="Sweep Limit")
    operating_percentage_field = ft.TextField(label="Operating Percentage")
    sweep_samples_field = ft.TextField(label="Sweep Samples")
    starting_current_field = ft.TextField(label="Starting Current")

    psu_address_field = ft.TextField(label="IP Address")
    psu_port_field = ft.TextField(label="Port")
    psu_timeout_field = ft.TextField(label="Timeout")
    psu_buffer_field = ft.TextField(label="Buffer")

    # Settings Page
    settings_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Settings",
                        theme_style=ft.TextThemeStyle.TITLE_LARGE,
                        text_align=ft.TextAlign.CENTER,
                        expand=True,
                    ),
                    alignment=ft.alignment.center,
                ),
                ft.GridView(
                    expand=0,
                    runs_count=2,
                    child_aspect_ratio=10,
                    controls=[
                        refining_period_field,
                        back_emf_period_field,
                        sweep_duration_field,
                        sample_period_field,
                        step_duration_field,
                        step_magnitude_field,
                        sweep_limit_field,
                        operating_percentage_field,
                        sweep_samples_field,
                        starting_current_field,
                    ],
                ),
                ft.Divider(),
                ft.Text(
                    "Power Supply Communcation",
                ),
                ft.GridView(
                    expand=0,
                    runs_count=2,
                    child_aspect_ratio=10,
                    controls=[
                        psu_address_field,
                        psu_port_field,
                        psu_timeout_field,
                        psu_buffer_field,
                    ],
                ),
            ],
            expand=True,
            alignment=ft.alignment.center,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )

    # Open Folder floating action button
    open_folder_fab = ft.FloatingActionButton(
        icon=ft.icons.FOLDER,
        mini=True,
        tooltip="Open working directory",
    )

    # Bottom Buttons, for quick actions
    refine_button = ft.NavigationDestination(
        label="Refining for 3:03",
        icon_content=ft.Icon(
            name="ELECTRIC_BOLT", color=ft.colors.RED_ACCENT_700
        ),
        selected_icon_content=ft.Icon(
            name="ELECTRIC_BOLT", color=ft.colors.ON_PRIMARY
        ),
    )

    emf_button = ft.NavigationDestination(
        label="Back Emf in 6:57",
        icon_content=ft.Icon(
            name="MOTION_PHOTOS_PAUSE", color=ft.colors.GREEN_ACCENT_700
        ),
        selected_icon_content=ft.Icon(
            name="MOTION_PHOTOS_PAUSE", color=ft.colors.ON_PRIMARY
        ),
    )

    sweep_button = ft.NavigationDestination(
        label="Sweep in 7:57",
        icon_content=ft.Icon(
            name="TRENDING_UP", color=ft.colors.BLUE_ACCENT_700
        ),
        selected_icon_content=ft.Icon(
            name="TRENDING_UP", color=ft.colors.ON_PRIMARY
        ),
    )

    bottom_navbar = ft.NavigationBar(
        selected_index=0,
        indicator_color=ft.colors.RED_ACCENT_700,
        bgcolor=ft.colors.ON_PRIMARY,
        destinations=[refine_button, emf_button, sweep_button],
    )
    page.add(bottom_navbar)

    # Start/Stop floating action button
    start_stop_fab = ft.FloatingActionButton(
        icon=ft.icons.POWER_OUTLINED, text="Start"
    )

    # Quick View button
    quick_view_button = ft.NavigationRailDestination(
        icon_content=ft.Icon(ft.icons.DASHBOARD_OUTLINED),
        selected_icon_content=ft.Icon(ft.icons.DASHBOARD),
        label="Quick View",
        padding=ft.padding.only(top=10),
    )

    # Run Summary button
    run_summary_button = ft.NavigationRailDestination(
        icon_content=ft.Icon(ft.icons.DATA_THRESHOLDING_OUTLINED),
        selected_icon_content=ft.Icon(ft.icons.DATA_THRESHOLDING),
        label="Run Summary",
    )

    # Sweep Summary
    sweeps_button = ft.NavigationRailDestination(
        icon_content=ft.Icon(ft.icons.TRENDING_UP_OUTLINED),
        selected_icon_content=ft.Icon(ft.icons.TRENDING_UP),
        label="Sweeps",
    )

    # Settings button
    settings_button = ft.NavigationRailDestination(
        icon_content=ft.Icon(ft.icons.SETTINGS_OUTLINED),
        selected_icon_content=ft.Icon(ft.icons.SETTINGS),
        label="Settings",
    )

    # Side Navigation Rail w/ Stop button
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        leading=start_stop_fab,
        destinations=[
            quick_view_button,
            run_summary_button,
            sweeps_button,
            settings_button,
        ],
        trailing=open_folder_fab,
        expand_loose=True,
        on_change=rail_change,
    )

    main_context = ft.Container(
        expand=True,
        alignment=ft.alignment.center,
        content=quick_view_container,
    )

    # Main Canvas
    page.add(
        ft.Row(
            [
                nav_rail,
                # Main context, switches contents to sub-pages
                main_context,
            ],
            expand=True,
            alignment=ft.alignment.bottom_center,
        )
    )


ft.app(main)
