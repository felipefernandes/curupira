import sys
import pytest
from unittest.mock import patch
from check_health import print_status, main

def test_print_status_output(capsys):
    print_status("Check Mem", "ok", "Mem normal")
    captured = capsys.readouterr()
    assert "✅" in captured.out
    assert "Mem normal" in captured.out

    print_status("Check Warn", "warning", "Cuidado")
    captured = capsys.readouterr()
    assert "⚠️" in captured.out

    print_status("Check Crit", "critical", "Falha G")
    captured = capsys.readouterr()
    assert "❌" in captured.out
    
    print_status("Check Unk", "unknown", "Misterio")
    captured = capsys.readouterr()
    assert "❓" in captured.out

@patch("check_health.run_full_diagnostic")
def test_main_healthy(mock_diag, capsys):
    mock_diag.return_value = {
        "status": "ok",
        "issues": [],
        "details": {"memory": "Ok"}
    }
    with patch.object(sys, "argv", ["check_health.py"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    cap = capsys.readouterr()
    assert "SAUDÁVEL" in cap.out

@patch("check_health.run_full_diagnostic")
def test_main_warning(mock_diag, capsys):
    mock_diag.return_value = {
        "status": "warning",
        "issues": ["Algum aviso"],
        "details": {"git": "unknown"}
    }
    with patch.object(sys, "argv", ["check_health.py"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
    cap = capsys.readouterr()
    assert "AVISO" in cap.out
    assert "Algum aviso" in cap.out

@patch("check_health.run_full_diagnostic")
def test_main_critical(mock_diag, capsys):
    mock_diag.return_value = {
        "status": "critical",
        "issues": ["Dependencia faltando"],
        "details": {"dependencies": "Dependencia faltando"}
    }
    with patch.object(sys, "argv", ["check_health.py", "--force"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
    
    mock_diag.assert_called_with(force=True)
    cap = capsys.readouterr()
    assert "CRÍTICO" in cap.out
    assert "Dependencia faltando" in cap.out
