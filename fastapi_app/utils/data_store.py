# fastapi_app/utils/data_store.py
import sqlite3
from datetime import datetime
from typing import Optional
import pandas as pd

import json

class DBlogger:
    def __init__(self, num_channels: int = 16, db_path="data/system.db"):
        self.num_channels = num_channels
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS channel_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            channel_id INTEGER,
            temperature REAL,
            target_temp REAL,
            kp REAL,
            ki REAL,
            kd REAL,
            control_period INTEGER,
            max_duty INTEGER,
            heating BOOLEAN
        )''')
        self.conn.commit()

    def log_data(self, channel_data: list):
        print(f"DEBUG - DBlogger: logging data for {len(channel_data)} channels")
        print(f"DEBUG - DBlogger: channel_data type: {type(channel_data)}")
        print(f"DEBUG - DBlogger: channel_data: {json.dumps(channel_data, indent=2)}")
        
        cursor = self.conn.cursor()
        now = datetime.now()
        
        try:
            for channel in channel_data:
                print(f"DEBUG - DBlogger: processing channel {channel.get('id')}")
                pid_params = channel.get('pid_params', {})
                print(f"DEBUG - DBlogger: pid_params: {pid_params}")
                
                try:
                    cursor.execute('''
                        INSERT INTO channel_logs (
                            timestamp, channel_id, temperature, target_temp,
                            kp, ki, kd, control_period, max_duty, heating
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        now,
                        channel.get('id'),
                        channel.get('temperature'),
                        pid_params.get('target_temp'),
                        pid_params.get('kp'),
                        pid_params.get('ki'),
                        pid_params.get('kd'),
                        pid_params.get('control_period'),
                        pid_params.get('max_duty'),
                        1 if channel.get('heating') else 0
                    ))
                    print(f"DEBUG - DBlogger: inserted data for channel {channel.get('id')}")
                except Exception as e:
                    print(f"DEBUG - DBlogger: error inserting channel {channel.get('id')}: {str(e)}")
                    raise
            
            self.conn.commit()
            print("DEBUG - DBlogger: committed all changes")
        except Exception as e:
            print(f"DEBUG - DBlogger: error in log_data: {str(e)}")
            import traceback
            print(f"DEBUG - DBlogger: traceback: {traceback.format_exc()}")
            raise

    def get_history(self, hours: int = 24, channel_id: Optional[int] = None) -> pd.DataFrame:
        query = '''
            SELECT * FROM channel_logs 
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours)
        
        if channel_id is not None:
            query += ' AND channel_id = {}'.format(channel_id)
        
        query += ' ORDER BY timestamp DESC'
        
        return pd.read_sql(query, self.conn)
        
    def clear_channel_data(self, channel_id: int) -> bool:
        """清空指定通道的所有数据
        
        Args:
            channel_id: 通道ID
            
        Returns:
            bool: 如果清空成功返回True，如果通道ID无效返回False
        """
        if not (0 <= channel_id < self.num_channels):
            print(f"DEBUG - DBlogger: 通道ID {channel_id} 超出范围 [0, {self.num_channels-1}]")
            return False
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM channel_logs WHERE channel_id = ?', (channel_id,))
            self.conn.commit()
            print(f"DEBUG - DBlogger: 已清空通道 {channel_id} 的所有数据")
            return True
        except Exception as e:
            print(f"DEBUG - DBlogger: 清空通道 {channel_id} 数据时出错: {str(e)}")
            import traceback
            print(f"DEBUG - DBlogger: traceback: {traceback.format_exc()}")
            self.conn.rollback()
            return False
        
    def clear_all_data(self) -> bool:
        """清空所有通道的所有数据
        
        Returns:
            bool: 清空成功返回True，失败返回False
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM channel_logs')
            self.conn.commit()
            print("DEBUG - DBlogger: 已清空所有通道的数据")
            return True
        except Exception as e:
            print(f"DEBUG - DBlogger: 清空所有数据时出错: {str(e)}")
            import traceback
            print(f"DEBUG - DBlogger: traceback: {traceback.format_exc()}")
            self.conn.rollback()
            return False