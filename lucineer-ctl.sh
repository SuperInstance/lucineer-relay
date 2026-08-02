#!/bin/bash
# lucineer-ctl.sh — Management script for the Lucineer Processor daemon
# Usage: ./lucineer-ctl.sh {start|stop|restart|status|logs|test}

SERVICE="lucineer-processor"
LOG_FILE="/home/eileen/projects/lucineer-worker/processor-daemon.log"
SCRIPT_DIR="/home/eileen/projects/lucineer-worker"

case "$1" in
    start)
        echo "Starting $SERVICE..."
        systemctl --user start "$SERVICE"
        echo "Status:"
        systemctl --user status "$SERVICE" --no-pager -l
        ;;

    stop)
        echo "Stopping $SERVICE..."
        systemctl --user stop "$SERVICE"
        echo "Stopped."
        ;;

    restart)
        echo "Restarting $SERVICE..."
        systemctl --user restart "$SERVICE"
        echo "Status:"
        systemctl --user status "$SERVICE" --no-pager -l
        ;;

    status)
        systemctl --user status "$SERVICE" --no-pager -l
        ;;

    logs)
        echo "=== Last 50 lines of processor-daemon.log ==="
        tail -50 "$LOG_FILE"
        ;;

    test)
        echo "=== Injecting mock job: 'build me a tower' ==="
        cd "$SCRIPT_DIR"
        python3 process_v2.py --mock "build me a tower"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs|test}"
        echo ""
        echo "Commands:"
        echo "  start    — Start the processor daemon"
        echo "  stop     — Stop the processor daemon"
        echo "  restart  — Restart the processor daemon"
        echo "  status   — Show daemon status"
        echo "  logs     — Tail last 50 lines of daemon log"
        echo "  test     — Inject a mock 'build me a tower' job"
        exit 1
        ;;
esac
