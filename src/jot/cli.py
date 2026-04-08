"""jot — YANP vault CLI."""

from __future__ import annotations

import sys

# Windows Terminal renders UTF-8 but Python defaults stdout to cp1252.
# Reconfigure to UTF-8 so Rich and click output non-ASCII characters correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click

from jot.commands.create import cmd_new, cmd_open, cmd_daily, cmd_weekly, cmd_monthly
from jot.commands.find import cmd_list, cmd_search, cmd_find, cmd_recent, cmd_stale, cmd_preview, cmd_pick
from jot.commands.capture import cmd_capture
from jot.commands.links import (
    cmd_links, cmd_backlinks, cmd_unresolved,
    cmd_repair_links, cmd_create_unresolved, cmd_graph, cmd_orphans,
)
from jot.commands.tags import cmd_tags, props_group
from jot.commands.organize import cmd_rename, cmd_merge, cmd_split, cmd_dedupe, cmd_related
from jot.commands.tasks import cmd_tasks, cmd_agenda
from jot.commands.views import cmd_dashboard, cmd_report, cmd_review
from jot.commands.template import template_group, query_group
from jot.commands.config_cmd import config_group
from jot.commands.publish import cmd_publish


@click.command("mcp")
def cmd_mcp() -> None:
    """Start the MCP server for AI model vault access."""
    from jot.mcp_server import main
    main()


@click.group()
@click.version_option(package_name="jot")
def cli() -> None:
    """jot — plain markdown notes, wikilinks, publish.\n
    Vault config: jot config init
    """


# Creating and opening
cli.add_command(cmd_new, "new")
cli.add_command(cmd_open, "open")
cli.add_command(cmd_daily, "daily")
cli.add_command(cmd_weekly, "weekly")
cli.add_command(cmd_monthly, "monthly")

# Finding
cli.add_command(cmd_list, "list")
cli.add_command(cmd_search, "search")
cli.add_command(cmd_find, "find")
cli.add_command(cmd_recent, "recent")
cli.add_command(cmd_stale, "stale")
cli.add_command(cmd_preview, "preview")
cli.add_command(cmd_pick, "pick")

# Quick capture
cli.add_command(cmd_capture, "capture")

# Links and graph
cli.add_command(cmd_links, "links")
cli.add_command(cmd_backlinks, "backlinks")
cli.add_command(cmd_unresolved, "unresolved")
cli.add_command(cmd_repair_links, "repair-links")
cli.add_command(cmd_create_unresolved, "create-unresolved")
cli.add_command(cmd_graph, "graph")
cli.add_command(cmd_orphans, "orphans")

# Tags and properties
cli.add_command(cmd_tags, "tags")
cli.add_command(props_group, "props")

# Organization
cli.add_command(cmd_rename, "rename")
cli.add_command(cmd_merge, "merge")
cli.add_command(cmd_split, "split")
cli.add_command(cmd_dedupe, "dedupe")
cli.add_command(cmd_related, "related")

# Tasks and agenda
cli.add_command(cmd_tasks, "tasks")
cli.add_command(cmd_agenda, "agenda")

# Views and reports
cli.add_command(cmd_dashboard, "dashboard")
cli.add_command(cmd_report, "report")
cli.add_command(cmd_review, "review")

# Templates and queries
cli.add_command(template_group, "template")
cli.add_command(query_group, "query")

# Config
cli.add_command(config_group, "config")

# Publish
cli.add_command(cmd_publish, "publish")

# MCP server
cli.add_command(cmd_mcp, "mcp")
