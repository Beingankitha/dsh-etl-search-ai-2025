"""
CLI application for ETL operations and system management.

This module provides command-line interface commands for:
- ETL pipeline execution
- Configuration validation
- Database management
- Supporting document processing
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import settings  # FIX: Import settings INSTANCE, not Settings class
from src.services.etl.etl_service import ETLService
from src.services.embeddings import IndexingService
from src.infrastructure import Database
from src.repositories import UnitOfWork
from src.logging_config import get_logger
from src.services.observability import (
    initialize_tracing,
    shutdown_tracing,
    TraceConfig,
    trace_async_function,
)

logger = get_logger(__name__)
console = Console()

# Create Typer app for CLI
app = typer.Typer(
    name="dsh-etl",
    help="DSH ETL Search AI - Dataset extraction, transformation, and loading CLI",
    pretty_exceptions_enable=False,
    no_args_is_help=True
)


@app.command()
def etl(
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of datasets to process"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging (DEBUG level)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Validate without committing to database"
    ),
    identifiers_file: Optional[str] = typer.Option(
        None,
        "--identifiers-file",
        "-f",
        help="Path to file containing dataset identifiers (one per line)"
    ),
    enable_supporting_docs: bool = typer.Option(
        True,
        "--enable-supporting-docs",
        help="Enable supporting document processing"
    ),
    enable_data_files: bool = typer.Option(
        True,
        "--enable-data-files",
        help="Enable dataset data file extraction"
    ),
):
    """
    Execute ETL pipeline: Extract metadata, Transform to models, Load to database
    
    Phases:
    1. EXTRACT: Fetch dataset identifiers and metadata documents from CEH Catalogue
    2. TRANSFORM: Parse XML/JSON/RDF/Schema.org into Dataset models
    3. LOAD: Upsert datasets and related entities into SQLite database
    
    Examples:
        uv run python cli_main.py etl --limit 10 --verbose
        uv run python cli_main.py etl --dry-run
        uv run python cli_main.py etl --identifiers-file custom_ids.txt --limit 5
        uv run dsh-etl etl --verbose
    """
    
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("[bold cyan]✓ Verbose logging enabled (DEBUG)[/bold cyan]")
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # Initialize tracing for CLI
    try:
        trace_config = TraceConfig(
            service_name="dsh-etl-cli",
            jaeger_host=settings.jaeger_host,
            jaeger_port=settings.jaeger_port,
            jaeger_enabled=settings.jaeger_enabled,
            environment=settings.jaeger_environment,
        )
        initialize_tracing(trace_config)
        console.print("[bold cyan]✓ Distributed tracing initialized[/bold cyan]")
    except Exception as e:
        console.print(f"[bold yellow]⚠ Tracing initialization warning: {e}[/bold yellow]")
    
    # FIX: Use settings instance, not Settings class
    ids_file = Path(identifiers_file) if identifiers_file else Path(settings.metadata_identifiers_file)
    
    if not ids_file.exists():
        console.print(f"[bold red]✗ Identifiers file not found: {ids_file}[/bold red]")
        raise typer.Exit(code=1)
    
    # Show configuration
    console.print("\n[bold blue]═══ DSH ETL Pipeline ═══[/bold blue]")
    config_table = Table(title="Configuration", show_header=True, header_style="bold magenta")
    config_table.add_column("Setting", style="cyan", width=30)
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Identifiers File", str(ids_file.absolute()))
    config_table.add_row("Database Path", settings.database_path)
    config_table.add_row("Batch Size", str(settings.batch_size))
    config_table.add_row("Max Concurrent Downloads", str(settings.max_concurrent_downloads))
    config_table.add_row("Limit", str(limit) if limit else "All identifiers")
    config_table.add_row("Supporting Docs", "✓ Enabled" if enable_supporting_docs else "✗ Disabled")
    config_table.add_row("Dry Run", "✓ Yes (no DB writes)" if dry_run else "✗ No (will commit)")
    config_table.add_row("Verbose", "✓ Yes" if verbose else "✗ No")
    config_table.add_row("Tracing", "✓ Enabled" if settings.jaeger_enabled else "✗ Disabled")
    
    console.print(config_table)
    
    # Run ETL pipeline
    try:
        try:
            asyncio.run(_run_etl(ids_file, limit, dry_run, enable_supporting_docs, enable_data_files))
            console.print("\n[bold green]✓ ETL Pipeline completed successfully[/bold green]\n")
        except KeyboardInterrupt:
            console.print("\n[bold yellow]⚠ Pipeline interrupted by user[/bold yellow]")
            raise typer.Exit(code=130)
        except Exception as e:
            console.print(f"\n[bold red]✗ ETL Pipeline failed: {e}[/bold red]")
            logger.exception("ETL pipeline error")
            raise typer.Exit(code=1)
    finally:
        # Shutdown tracing
        try:
            shutdown_tracing()
            console.print("[bold cyan]✓ Distributed tracing shutdown[/bold cyan]")
        except Exception as e:
            console.print(f"[bold yellow]⚠ Tracing shutdown warning: {e}[/bold yellow]")


@trace_async_function(attributes={"component": "cli", "operation": "etl_pipeline"})
async def _run_etl(
    identifiers_file: Path,
    limit: Optional[int],
    dry_run: bool,
    enable_supporting_docs: bool,
    enable_data_files: bool
):
    """Internal async function to run ETL pipeline"""
    
    try:
        # FIX: Use settings instance
        db_path = Path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db_manager = Database(settings.database_path)
        db_manager.create_tables()
        console.print("[bold green]✓ Database initialized[/bold green]")
        
        unit_of_work = UnitOfWork(db_manager)
        
        # Create ETL service
        etl_service = ETLService(
            identifiers_file=identifiers_file,
            unit_of_work=unit_of_work,
            batch_size=settings.batch_size,
            max_concurrent_downloads=settings.max_concurrent_downloads,
            dry_run=dry_run,
            enable_supporting_docs=enable_supporting_docs,
            enable_data_files=enable_data_files,
            enable_adaptive_batching=True,
            enable_error_recovery=True
        )
        
        # Run pipeline
        console.print("\n[bold cyan]→ Starting ETL Pipeline...[/bold cyan]\n")
        
        report = await etl_service.run_pipeline(limit=limit)
        
        # Display results
        _display_report(report, dry_run)
        
    except Exception as e:
        logger.exception("ETL execution error")
        raise


def _display_report(report: dict, dry_run: bool):
    """Display ETL pipeline results"""
    
    console.print("\n[bold blue]═══ ETL Pipeline Complete ═══[/bold blue]")
    
    results_table = Table(title="Pipeline Results", show_header=True, header_style="bold magenta")
    results_table.add_column("Metric", style="cyan", width=30)
    results_table.add_column("Count", style="green", justify="right")
    
    results_table.add_row("Total Identifiers", str(report.get('total_identifiers', 0)))
    results_table.add_row("Successfully Processed", str(report.get('successful', 0)))
    results_table.add_row("Failed", str(report.get('failed', 0)))
    results_table.add_row("Metadata Extracted", str(report.get('metadata_extracted', 0)))
    results_table.add_row("Supporting Docs Found", str(report.get('supporting_docs_found', 0)))
    results_table.add_row("Supporting Docs Downloaded", str(report.get('supporting_docs_downloaded', 0)))
    results_table.add_row("Text Extracted", str(report.get('text_extracted', 0)))
    results_table.add_row("Data Files Extracted", str(report.get('data_files_extracted', 0)))
    results_table.add_row("Data Files Stored", str(report.get('data_files_stored', 0)))
    
    # Add cache statistics to main results table
    metadata_cache_stats = report.get('metadata_cache_stats', {})
    if metadata_cache_stats:
        results_table.add_row("", "")  # Empty row for spacing
        results_table.add_row("Cache Hits", str(metadata_cache_stats.get('hits', 0)), style="bold cyan")
        results_table.add_row("Cache Misses", str(metadata_cache_stats.get('misses', 0)))
        results_table.add_row("Hit Rate", str(metadata_cache_stats.get('hit_rate', '0%')))
    
    results_table.add_row("Duration (seconds)", f"{report.get('duration', 0):.2f}")
    
    console.print(results_table)
    
    # Show detailed cache breakdown by metadata type
    if metadata_cache_stats and metadata_cache_stats.get('by_format'):
        console.print("\n[bold cyan]Cache Breakdown by Metadata Type:[/bold cyan]")
        cache_table = Table(show_header=True, header_style="bold cyan", box=None)
        cache_table.add_column("Format", style="magenta", width=15)
        cache_table.add_column("Hits", justify="right", style="green")
        cache_table.add_column("Misses", justify="right", style="yellow")
        cache_table.add_column("Hit Rate", justify="right", style="cyan")
        
        for fmt, stats in metadata_cache_stats['by_format'].items():
            cache_table.add_row(
                fmt.upper(),
                str(stats['hits']),
                str(stats['misses']),
                str(stats['hit_rate'])
            )
        
        console.print(cache_table)
    
    # Show errors if any
    if report.get('errors'):
        console.print("\n[bold yellow]⚠ Errors Encountered:[/bold yellow]")
        for i, error in enumerate(report['errors'][:10], 1):
            msg = error.get('message', str(error))[:75]
            identifier = error.get('identifier', 'unknown')[:30]
            console.print(f"  {i:2d}. {identifier}: {msg}")
        
        if len(report['errors']) > 10:
            console.print(f"  ... and {len(report['errors']) - 10} more errors")
    
    # Dry run notice
    if dry_run:
        console.print("\n[bold yellow]ℹ DRY RUN MODE - No data was committed to database[/bold yellow]")
    else:
        console.print("\n[bold green]✓ Data successfully committed to database[/bold green]")


@app.command()
def validate_config(
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose output"
    ),
):
    """Validate configuration and show environment settings"""
    console.print("\n[bold blue]═══ Configuration Validation ═══[/bold blue]\n")
    
    config_table = Table(title="Current Configuration", show_header=True, header_style="bold magenta")
    config_table.add_column("Property", style="cyan", width=35)
    config_table.add_column("Value", style="green")
    
    # FIX: Use settings instance
    config_table.add_row("App Name", settings.app_name)
    config_table.add_row("Environment", settings.environment)
    config_table.add_row("CEH API Base URL", settings.ceh_api_base_url)
    config_table.add_row("Database Path", settings.database_path)
    config_table.add_row("Batch Size", str(settings.batch_size))
    config_table.add_row("Max Concurrent Downloads", str(settings.max_concurrent_downloads))
    config_table.add_row("Metadata Identifiers File", settings.metadata_identifiers_file)
    config_table.add_row("Supporting Docs Dir", str(settings.supporting_docs_dir))
    config_table.add_row("Debug", str(settings.debug))
    
    console.print(config_table)
    console.print("\n[bold green]✓ Configuration is valid[/bold green]\n")


@app.command()
def init_db():
    """Initialize or reset the database"""
    console.print("\n[bold blue]═══ Database Initialization ═══[/bold blue]\n")
    
    # FIX: Use settings instance
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    db_manager = Database(settings.database_path)
    db_manager.create_tables()
    
    console.print("[bold green]✓ Database initialized successfully[/bold green]")
    console.print(f"  Database path: {db_path.absolute()}\n")


@app.command()
def check_supporting_docs(
    identifier: Optional[str] = typer.Option(
        None,
        "--identifier",
        "-id",
        help="Filter by specific dataset identifier"
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed document list"
    )
):
    """Check which supporting documents are linked to which identifiers"""
    import sqlite3
    
    db_path = Path(settings.database_path)
    if not db_path.exists():
        console.print("[bold red]✗ Database not found[/bold red]")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    console.print("\n[bold blue]╔════════════════════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║  Supporting Documents per Identifier                  ║[/bold blue]")
    console.print("[bold blue]╚════════════════════════════════════════════════════════╝[/bold blue]\n")
    
    # Query: Show each identifier with its supporting documents count
    query = """
    SELECT 
        d.file_identifier,
        d.title,
        COUNT(sd.id) as doc_count
    FROM datasets d
    LEFT JOIN supporting_documents sd ON d.id = sd.dataset_id
    """
    
    params = []
    if identifier:
        query += "WHERE d.file_identifier LIKE ?"
        params.append(f"%{identifier}%")
    
    query += "GROUP BY d.id, d.file_identifier, d.title ORDER BY doc_count DESC, d.file_identifier"
    
    cursor.execute(query, params)
    
    table = Table(title="Supporting Documents Summary", show_header=True, header_style="bold cyan")
    table.add_column("Identifier", style="magenta", width=40)
    table.add_column("Title", width=50)
    table.add_column("Doc Count", justify="right", style="green")
    
    for row in cursor.fetchall():
        table.add_row(
            row['file_identifier'][:36],
            row['title'][:47],
            str(row['doc_count'])
        )
    
    console.print(table)
    
    if detailed:
        console.print("\n[bold blue]╔════════════════════════════════════════════════════════╗[/bold blue]")
        console.print("[bold blue]║  Detailed Document List                                ║[/bold blue]")
        console.print("[bold blue]╚════════════════════════════════════════════════════════╝[/bold blue]\n")
        
        query2 = """
        SELECT 
            d.file_identifier,
            sd.title as doc_title,
            sd.document_url,
            sd.file_extension,
            LENGTH(sd.text_content) as text_bytes
        FROM supporting_documents sd
        JOIN datasets d ON sd.dataset_id = d.id
        """
        
        params2 = []
        if identifier:
            query2 += "WHERE d.file_identifier LIKE ?"
            params2.append(f"%{identifier}%")
        
        query2 += "ORDER BY d.file_identifier, sd.title"
        
        cursor.execute(query2, params2)
        for row in cursor.fetchall():
            console.print(f"[magenta]{row['file_identifier'][:36]}[/magenta] → {row['doc_title'][:50]}")
            console.print(f"  URL: {row['document_url'][:60]}")
            console.print(f"  Type: {row['file_extension'] or 'N/A'} | Text: {row['text_bytes']:,} bytes\n")
    
    # Summary stats
    console.print("[bold blue]╔════════════════════════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║  Summary Statistics                                   ║[/bold blue]")
    console.print("[bold blue]╚════════════════════════════════════════════════════════╝[/bold blue]\n")
    
    cursor.execute("SELECT COUNT(DISTINCT dataset_id) FROM supporting_documents")
    datasets_with_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM supporting_documents")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(LENGTH(text_content)) FROM supporting_documents")
    total_text_bytes = cursor.fetchone()[0] or 0
    
    console.print(f"Total Datasets with Supporting Docs: [green]{datasets_with_docs}[/green]")
    console.print(f"Total Supporting Documents: [green]{total_docs}[/green]")
    console.print(f"Total Text Content Size: [green]{total_text_bytes / 1024 / 1024:.2f} MB[/green]\n")
    
    conn.close()


@app.command()
def index(
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Enable verbose logging (DEBUG level)"
    ),
    supporting_docs: bool = typer.Option(
        True,
        "--supporting-docs",
        help="Index supporting documents for RAG"
    ),
    clear_first: bool = typer.Option(
        False,
        "--clear-first",
        help="Clear vector store before indexing"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of datasets to index (for testing)"
    ),
):
    """
    Index all datasets into vector store for semantic search.
    
    Process:
    1. Load datasets from SQLite database
    2. Generate embeddings for metadata (title + abstract + keywords)
    3. Store in ChromaDB vector database
    4. Optionally process supporting documents for RAG
    
    Examples:
        uv run python cli_main.py index --verbose
        uv run python cli_main.py index --clear-first
        uv run python cli_main.py index --supporting-docs --limit 10
        uv run dsh-etl index --verbose
    """
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("[bold cyan]✓ Verbose logging enabled (DEBUG)[/bold cyan]")
    
    console.print("\n[bold blue]═══════════════════════════════════════[/bold blue]")
    console.print("[bold blue]  Vector Store Indexing Pipeline[/bold blue]")
    console.print("[bold blue]═══════════════════════════════════════[/bold blue]\n")
    
    try:
        # Initialize services
        db = Database()
        db.connect()
        
        indexing_service = IndexingService(
            database=db,
            extract_supporting_docs=supporting_docs
        )
        
        # Clear vector store if requested
        if clear_first:
            console.print("[yellow]⚠  Clearing existing vector store...[/yellow]")
            indexing_service.vector_store.clear_all()
            console.print("[bold green]✓ Vector store cleared[/bold green]\n")
        
        # Run indexing pipeline
        console.print("[cyan]▶ Starting indexing pipeline...[/cyan]\n")
        progress = indexing_service.index_all_datasets(supporting_docs=supporting_docs)
        
        # Display results table
        table = Table(title="[bold]Indexing Results[/bold]", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="bold")
        
        table.add_row(
            "Total Datasets in DB",
            str(progress.total_datasets),
            "✓" if progress.total_datasets > 0 else "✗"
        )
        table.add_row(
            "Datasets Indexed",
            str(progress.total_indexed),
            "✓" if progress.total_indexed > 0 else "✗"
        )
        table.add_row(
            "Success Rate",
            f"{progress.success_rate:.1f}%",
            "✓" if progress.success_rate >= 90 else "⚠"
        )
        
        if supporting_docs:
            table.add_row(
                "Supporting Docs Processed",
                str(progress.total_docs),
                "✓"
            )
            table.add_row(
                "Doc Chunks Indexed",
                str(progress.total_docs_indexed),
                "✓" if progress.total_docs_indexed > 0 else "⚠"
            )
        
        if progress.errors:
            table.add_row(
                "Errors",
                str(len(progress.errors)),
                "⚠"
            )
        
        if progress.duration_seconds:
            table.add_row(
                "Duration",
                f"{progress.duration_seconds:.1f}s",
                "✓"
            )
        
        console.print(table)
        
        # Display vector store stats
        console.print("\n[bold cyan]Vector Store Statistics:[/bold cyan]")
        datasets_in_store = indexing_service.vector_store.get_dataset_count()
        docs_in_store = indexing_service.vector_store.get_supporting_docs_count()
        
        console.print(f"  • Datasets in vector store: [green]{datasets_in_store}[/green]")
        console.print(f"  • Doc chunks in vector store: [green]{docs_in_store}[/green]")
        
        # Display errors if any
        if progress.errors:
            console.print("\n[yellow]⚠  Errors encountered:[/yellow]")
            for i, error in enumerate(progress.errors[:10], 1):
                console.print(f"  {i}. {error}")
            if len(progress.errors) > 10:
                console.print(f"  ... and {len(progress.errors) - 10} more")
        
        console.print(f"\n[bold green]✓ Indexing pipeline complete![/bold green]\n")
        
    except Exception as e:
        console.print(f"[bold red]✗ Indexing failed: {e}[/bold red]\n")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


if __name__ == '__main__':
    app()