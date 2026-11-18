import typer
from typer import Option

app = typer.Typer()

def main(name: str = Option("x")) -> None:
    reveal_type(typer.Option)
    typer.echo(name)
