"""
Sistema de tracking de posiciones con SQLite
Maneja 1 posición activa a la vez
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict
import os


class PositionTracker:
    """Gestiona posiciones activas en base de datos SQLite"""
    
    def __init__(self, db_path: str = "positions.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Crea la tabla de posiciones si no existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                sl_price REAL NOT NULL,
                tp_price REAL NOT NULL,
                capital_percent REAL DEFAULT 10.0,
                leverage INTEGER DEFAULT 10,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                ma7 REAL,
                ma25 REAL,
                confidence TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def open_position(self, symbol: str, direction: str, entry_price: float,
                     sl_price: float, tp_price: float, ma7: float = None,
                     ma25: float = None, confidence: str = 'MEDIUM') -> int:
        """
        Abre una nueva posición
        
        Args:
            symbol: Par de trading (ej: BTC/USDT)
            direction: 'LONG' o 'SHORT'
            entry_price: Precio de entrada
            sl_price: Precio de stop loss
            tp_price: Precio de take profit
            ma7: Valor MA7 al momento de entrada
            ma25: Valor MA25 al momento de entrada
            confidence: Nivel de confianza ('HIGH', 'MEDIUM', 'LOW')
        
        Returns:
            int: ID de la posición creada
        """
        # Verificar que no haya otra posición activa
        active = self.get_active_position()
        if active:
            raise Exception(f"Ya existe una posición activa: {active['symbol']}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO positions 
            (symbol, direction, entry_price, sl_price, tp_price, ma7, ma25, confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (symbol, direction, entry_price, sl_price, tp_price, ma7, ma25, confidence))
        
        position_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return position_id
    
    def get_active_position(self) -> Optional[Dict]:
        """
        Obtiene la posición activa actual
        
        Returns:
            dict o None: Datos de la posición activa
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM positions 
            WHERE status = 'ACTIVE' 
            ORDER BY opened_at DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def close_position(self, position_id: int, reason: str = 'MANUAL') -> bool:
        """
        Cierra una posición
        
        Args:
            position_id: ID de la posición
            reason: Razón del cierre ('TP', 'SL', 'CROSS_REVERSE', 'MANUAL')
        
        Returns:
            bool: True si se cerró correctamente
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE positions 
            SET status = ?
            WHERE id = ?
        """, (f'CLOSED_{reason}', position_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def get_position_by_id(self, position_id: int) -> Optional[Dict]:
        """Obtiene una posición por ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_positions(self, limit: int = 50) -> list:
        """Obtiene todas las posiciones (historial)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM positions 
            ORDER BY opened_at DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def calculate_pnl(self, position: Dict, current_price: float) -> Dict:
        """
        Calcula el P&L actual de una posición
        
        Args:
            position: Dict con datos de la posición
            current_price: Precio actual del activo
        
        Returns:
            dict: {
                'pnl_percent': float,
                'pnl_usd': float (estimado con 10% de capital),
                'status': 'profit' / 'loss' / 'breakeven'
            }
        """
        entry = position['entry_price']
        direction = position['direction']
        
        if direction == 'LONG':
            pnl_percent = ((current_price - entry) / entry) * 100
        else:  # SHORT
            pnl_percent = ((entry - current_price) / entry) * 100
        
        # Estimación simple (asumiendo $1000 capital total, 10% = $100, 10x leverage = $1000 posición)
        # P&L = posición_size * (pnl_percent / 100)
        pnl_usd = 1000 * (pnl_percent / 100)
        
        status = 'breakeven'
        if pnl_percent > 0.5:
            status = 'profit'
        elif pnl_percent < -0.5:
            status = 'loss'
        
        return {
            'pnl_percent': round(pnl_percent, 2),
            'pnl_usd': round(pnl_usd, 2),
            'status': status
        }
