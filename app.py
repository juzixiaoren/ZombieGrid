from service.cli import run_cli
from dao.db_function_library import init_db
if __name__ == "__main__":
    print("网格交易神器")
    init_db()
    run_cli()