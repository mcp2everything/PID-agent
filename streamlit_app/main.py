import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import time
import io
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(page_title='PID多通道控制面板', layout='wide')

# API配置
API_BASE = 'http://localhost:8000/api'

# 获取可用串口列表
def get_available_ports():
    try:
        print("DEBUG - Frontend: Getting available ports")
        response = requests.get(f'{API_BASE}/device/ports')
        if response.status_code == 200:
            data = response.json()
            st.session_state.available_ports = data['ports']
            st.session_state.baudrates = data['baudrates']
            st.session_state.virtual_port = data['virtual_port']
            print(f"DEBUG - Frontend: Got ports: {st.session_state.available_ports}")
            print(f"DEBUG - Frontend: Got baudrates: {st.session_state.baudrates}")
            return True
    except Exception as e:
        print(f"DEBUG - Frontend: Failed to get ports: {str(e)}")
        st.error(f'获取串口列表失败: {str(e)}')
    return False

# 初始化session状态
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'num_channels' not in st.session_state:
    st.session_state.num_channels = 16
if 'selected_channel' not in st.session_state:
    st.session_state.selected_channel = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = 0
if 'update_interval' not in st.session_state:
    st.session_state.update_interval = 1.0  # 默认 1 秒更新一次
if 'collecting' not in st.session_state:
    st.session_state.collecting = False  # 采集状态
if 'data_points' not in st.session_state:
    st.session_state.data_points = []  # 实时数据点
if 'update_counter' not in st.session_state:
    st.session_state.update_counter = 0  # 用于触发自动更新
if 'available_ports' not in st.session_state:
    st.session_state.available_ports = []  # 可用串口列表
if 'baudrates' not in st.session_state:
    st.session_state.baudrates = []  # 支持的波特率列表
if 'virtual_port' not in st.session_state:
    st.session_state.virtual_port = ""  # 虚拟串口名称
    
# 首次启动时自动获取串口列表
if not st.session_state.initialized:
    get_available_ports()
    st.session_state.initialized = True

# 实时数据更新
def update_data():
    if not st.session_state.collecting:
        return None
        
    try:
        print("DEBUG - Frontend: Fetching device status")
        response = requests.get(f'{API_BASE}/device/status')
        print(f"DEBUG - Frontend: Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG - Frontend: Got data: {data}")
            # 更新数据点
            st.session_state.data_points.append(data)
            # 只保留最近100个点
            if len(st.session_state.data_points) > 100:
                st.session_state.data_points = st.session_state.data_points[-100:]
            # 更新最后更新时间
            st.session_state.last_update = time.time()
            # 增加更新计数器
            st.session_state.update_counter += 1
            print(f"DEBUG - Frontend: Updated counter to {st.session_state.update_counter}")
            return data
        elif response.status_code == 400:
            print("DEBUG - Frontend: Device disconnected")
            st.session_state.connected = False
            st.session_state.collecting = False
            st.error('设备连接已断开，请重新连接')
        else:
            error_detail = response.json().get("detail", "未知错误")
            print(f"DEBUG - Frontend: Error getting status: {error_detail}")
            st.error(f'获取设备状态失败: {error_detail}')
    except Exception as e:
        print(f"DEBUG - Frontend: Exception: {str(e)}")
        st.error(f'获取设备状态失败: {str(e)}')
    return None

# 获取可用串口列表
def get_available_ports():
    try:
        print("DEBUG - Frontend: Getting available ports")
        response = requests.get(f'{API_BASE}/device/ports')
        if response.status_code == 200:
            data = response.json()
            st.session_state.available_ports = data['ports']
            st.session_state.baudrates = data['baudrates']
            st.session_state.virtual_port = data['virtual_port']
            print(f"DEBUG - Frontend: Got ports: {st.session_state.available_ports}")
            print(f"DEBUG - Frontend: Got baudrates: {st.session_state.baudrates}")
            return True
    except Exception as e:
        print(f"DEBUG - Frontend: Failed to get ports: {str(e)}")
        st.error(f'获取串口列表失败: {str(e)}')
    return False

# 断开设备连接
def disconnect_device():
    try:
        print("DEBUG - Frontend: Disconnecting device")
        response = requests.post(f'{API_BASE}/device/disconnect')
        if response.status_code == 200:
            print("DEBUG - Frontend: Device disconnected successfully")
            st.session_state.connected = False
            st.session_state.collecting = False
            st.session_state.data_points = []
            st.rerun()
            return True
    except Exception as e:
        print(f"DEBUG - Frontend: Failed to disconnect: {str(e)}")
        st.error(f'断开连接失败: {str(e)}')
    return False

# 连接设备
def connect_device(port: str, baudrate: int, num_channels: int, use_mock: bool):
    try:
        print("DEBUG - Frontend: Connecting to device")
        print(f"DEBUG - Frontend: port={port}, baudrate={baudrate}, num_channels={num_channels}, use_mock={use_mock}")
        
        response = requests.post(
            f'{API_BASE}/device/connect',
            json={
                'port': port,
                'baudrate': baudrate,
                'num_channels': num_channels,
                'use_mock': use_mock
            }
        )
        print(f"DEBUG - Frontend: Connect response status: {response.status_code}")
        
        if response.status_code == 200:
            print("DEBUG - Frontend: Device connected successfully")
            st.session_state.connected = True
            st.session_state.num_channels = num_channels
            st.rerun()
            return True
        else:
            error_detail = response.json().get("detail", "未知错误")
            print(f"DEBUG - Frontend: Connection failed: {error_detail}")
            st.error(f'连接失败: {error_detail}')
    except Exception as e:
        print(f"DEBUG - Frontend: Connection exception: {str(e)}")
        st.error(f'连接失败: {str(e)}')
    return False

# 侧边栏 - 设备控制
with st.sidebar:
    st.header('设备控制')
    
    # 更新频率控制
    st.session_state.update_interval = st.slider('更新频率(秒)', 0.5, 10.0, st.session_state.update_interval)
    
    # 获取串口列表
    if st.button('刷新串口列表'):
        get_available_ports()
    
    # 设备连接控制
    # 选择串口
    port_options = [(p['port'], p['description']) for p in st.session_state.available_ports]
    if st.session_state.virtual_port:
        port_options.append(('VIRTUAL', '虚拟串口'))
    
    if not port_options:
        st.warning('未发现串口设备，请点击刷新按钮')
        port = 'VIRTUAL'
        use_mock = True
    else:
        selected_port = st.selectbox('选择串口', 
                                  port_options, 
                                  format_func=lambda x: f'{x[0]} ({x[1]})',
                                  disabled=st.session_state.connected)
        port = selected_port[0] if selected_port else None
        use_mock = port == 'VIRTUAL'
    
    # 选择波特率
    if st.session_state.baudrates:
        baudrate = st.selectbox('波特率', 
                              st.session_state.baudrates, 
                              index=len(st.session_state.baudrates)-1,
                              disabled=st.session_state.connected)
    else:
        baudrate = 115200  # 默认值
    
    # 设置通道数
    num_channels = st.number_input('通道数', 
                                min_value=1, 
                                max_value=32, 
                                value=16,
                                disabled=st.session_state.connected)
    
    # 连接/断开按钮
    if not st.session_state.connected:
        if st.button('连接设备', use_container_width=True):
            if port:
                connect_device(port, baudrate, num_channels, use_mock)
            else:
                st.error('请选择串口')
    else:
        if st.button('断开连接', type='secondary', use_container_width=True):
            disconnect_device()
    
    # 采集控制
    if st.session_state.connected:
        col1, col2 = st.columns(2)
        with col1:
            if not st.session_state.collecting:
                if st.button('开始采集', type='primary'):
                    st.session_state.collecting = True
                    st.session_state.last_update = 0  # 重置更新时间
        with col2:
            if st.session_state.collecting:
                if st.button('停止采集', type='secondary'):
                    st.session_state.collecting = False
                    
        # 数据清理控制
        st.divider()
        st.subheader('数据管理')
        col1, col2 = st.columns(2)
        with col1:
            if st.button('清空当前通道', type='secondary'):
                try:
                    response = requests.delete(f'{API_BASE}/device/channel/{st.session_state.selected_channel}/data')
                    if response.status_code == 200:
                        st.success(f'已清空通道 {st.session_state.selected_channel} 的数据')
                    else:
                        st.error(f'清空数据失败: {response.text}')
                except Exception as e:
                    st.error(f'清空数据出错: {str(e)}')
        with col2:
            if st.button('清空所有数据', type='secondary'):
                try:
                    response = requests.delete(f'{API_BASE}/device/data')
                    if response.status_code == 200:
                        st.success('已清空所有通道的数据')
                    else:
                        st.error(f'清空数据失败: {response.text}')
                except Exception as e:
                    st.error(f'清空数据出错: {str(e)}')
    
    # 连接状态
    if not st.session_state.connected:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.num_channels = st.number_input('通道数量', 1, 32, 16)
        with col2:
            st.session_state.use_mock = st.checkbox('使用虚拟数据', value=True)
        
        if st.button('连接设备', type='primary'):
            if connect_device():
                st.success('设备连接成功' + (' (虚拟模式)' if st.session_state.use_mock else ''))
    
    # 通道选择
    if st.session_state.connected:
        st.session_state.selected_channel = st.selectbox(
            '选择通道',
            range(st.session_state.num_channels),
            format_func=lambda x: f'通道 {x}'
        )
        
        # PID参数调整
        st.subheader('PID参数设置')
        
        # 初始化状态
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        if 'apply_status' not in st.session_state:
            st.session_state.apply_status = None
            
        # 创建两个列来放置按钮
        col1, col2 = st.columns(2)
        
        # 分析按钮
        with col1:
            if st.button('使用AI优化PID参数'):
                try:
                    with st.spinner('正在分析数据...'):
                        response = requests.post(
                            f'{API_BASE}/optimization/channel/{st.session_state.selected_channel}/optimize',
                            json={'hours': 1}  # 分析最近1小时的数据
                        )
                        print(f"DEBUG - Frontend: 优化响应: {response.text}")
                        
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                if isinstance(result, dict):
                                    st.session_state.analysis_result = result
                                    st.session_state.analysis_complete = True
                                    st.session_state.apply_status = None
                                    st.success('AI分析完成')
                                else:
                                    st.error('响应格式错误，需要JSON对象')
                                    print(f"DEBUG - Frontend: 响应不是字典: {result}")
                            except ValueError as e:
                                st.error('响应不是有效的JSON格式')
                                print(f"DEBUG - Frontend: JSON解析错误: {str(e)}")
                        else:
                            st.error('AI分析失败')
                            print(f"DEBUG - Frontend: 请求失败: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f'分析出错: {str(e)}')
                    print(f"DEBUG - Frontend: 未知错误: {str(e)}")
        
        # 应用优化按钮
        with col2:
            if st.session_state.analysis_complete:
                if st.button('应用优化建议'):
                    try:
                        print(f"DEBUG - Frontend: analysis_result类型: {type(st.session_state.analysis_result)}")
                        print(f"DEBUG - Frontend: analysis_result内容: {st.session_state.analysis_result}")
                        
                        if isinstance(st.session_state.analysis_result, dict):
                            # 解析ai_suggestion字符串
                            try:
                                ai_suggestion = json.loads(st.session_state.analysis_result.get('ai_suggestion', '{}'))
                                print(f"DEBUG - Frontend: 解析后的ai_suggestion: {ai_suggestion}")
                                
                                params = ai_suggestion.get('pid_command', {})
                                print(f"DEBUG - Frontend: 提取的params: {params}")
                                
                                if params:
                                    api_url = f'{API_BASE}/device/channel/{st.session_state.selected_channel}/pid'
                                    
                                    with st.spinner('正在应用PID参数...'):
                                        print(f"DEBUG - Frontend: 应用参数api_url: {str(api_url)}")
                                        print(f"DEBUG - Frontend: 应用参数params: {str(params)}")
                                        response = requests.post(api_url, json=params)
                                        if response.status_code == 200:
                                            st.session_state.apply_status = 'success'
                                            st.session_state.current_pid_params.update(params)
                                            st.success('已应用优化建议的PID参数')
                                            st.rerun()
                                        else:
                                            st.session_state.apply_status = 'error'
                                            st.error(f'应用参数失败: {response.text}')
                                            print(f"DEBUG - Frontend: 应用参数失败: {str(response.text)}")
                                else:
                                    st.session_state.apply_status = 'error'
                                    st.error('无法获取PID参数，请检查优化结果格式')
                            except json.JSONDecodeError as e:
                                st.session_state.apply_status = 'error'
                                st.error(f'AI建议解析错误: {str(e)}')
                                print(f"DEBUG - Frontend: JSON解析错误: {str(e)}")
                        else:
                            st.session_state.apply_status = 'error'
                            st.error('分析结果格式错误，请重新分析')
                    except Exception as e:
                        st.session_state.apply_status = 'error'
                        st.error(f'应用参数失败: {str(e)}')
        
        # 分析结果显示
        if st.session_state.analysis_complete:
            st.markdown('### 分析结果')
            
            # 显示温度曲线分析
            st.markdown('#### 温度曲线分析')
            st.write(st.session_state.analysis_result.get('curve_analysis', {}))
            
            # 显示PID参数优化建议
            st.markdown('#### PID参数优化建议')
            st.write(st.session_state.analysis_result.get('params_optimization', {}))
            
            # 显示AI综合建议
            st.markdown('#### AI综合建议')
            st.write(st.session_state.analysis_result.get('ai_suggestion', {}))
            
            # # 如果有调试信息，显示它
            # if st.session_state.apply_status:
            #     st.markdown('#### 调试信息')
            #     try:
            #         params = st.session_state.analysis_result.get('ai_suggestion', {}).get('pid_command', {})
            #         st.write('1. PID参数：', params)
            #         st.write('2. 请求URL：', f'{API_BASE}/device/channel/{st.session_state.selected_channel}/pid')
            #     except Exception as e:
            #         st.error(f'无法显示调试信息: {str(e)}')
        
        # 手动PID参数调整表单
        with st.form(key='pid_form'):
            # 使用session state来存储当前值
            if 'current_pid_params' not in st.session_state:
                st.session_state.current_pid_params = {
                    'kp': 1.0,
                    'ki': 0.1,
                    'kd': 0.05,
                    'target_temp': 25.0,
                    'control_period': 100,
                    'max_duty': 80
                }
            
            # 如果有新的AI建议参数且已经应用，更新当前值
            if st.session_state.get('analysis_complete') and st.session_state.get('apply_status') == 'success':
                try:
                    params = st.session_state.analysis_result.get('ai_suggestion', {}).get('pid_command', {})
                    if params:
                        st.session_state.current_pid_params.update(params)
                        # 清除应用状态，避免重复更新
                        st.session_state.apply_status = None
                except Exception as e:
                    print(f"DEBUG - Frontend: 更新PID参数出错: {str(e)}")
            
            # 使用当前值作为默认值
            kp = st.number_input('Kp', 0.0, 100.0, st.session_state.current_pid_params['kp'])
            ki = st.number_input('Ki', 0.0, 100.0, st.session_state.current_pid_params['ki'])
            kd = st.number_input('Kd', 0.0, 100.0, st.session_state.current_pid_params['kd'])
            target_temp = st.number_input('目标温度', 0.0, 200.0, st.session_state.current_pid_params['target_temp'])
            control_period = st.number_input('控制周期(ms)', 10, 1000, st.session_state.current_pid_params['control_period'])
            max_duty = st.number_input('最大占空比(%)', 0, 100, st.session_state.current_pid_params['max_duty'])
            
            if st.form_submit_button('手动更新PID参数'):
                try:
                    response = requests.post(
                        f'{API_BASE}/device/channel/{st.session_state.selected_channel}/pid',
                        json={
                            'kp': kp,
                            'ki': ki,
                            'kd': kd,
                            'target_temp': target_temp,
                            'control_period': control_period,
                            'max_duty': max_duty
                        }
                    )
                    if response.status_code == 200:
                        st.success('PID参数更新成功')
                    else:
                        st.error('参数更新失败')
                except:
                    st.error('通信失败')        
        # 加热控制
        col1, col2 = st.columns(2)
        with col1:
            if st.button('开始加热', key=f'heat_start_{st.session_state.selected_channel}', type='primary'):
                try:
                    print(f"DEBUG - Frontend: Starting heating for channel {st.session_state.selected_channel}")
                    response = requests.post(
                        f'{API_BASE}/device/channel/{st.session_state.selected_channel}/control',
                        json={'heating': True}
                    )
                    print(f"DEBUG - Frontend: Heating response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("DEBUG - Frontend: Heating started successfully")
                        st.success('开始加热')
                    else:
                        error_detail = response.json().get("detail", "未知错误")
                        print(f"DEBUG - Frontend: Heating failed: {error_detail}")
                        st.error(f'开始加热失败: {error_detail}')
                except Exception as e:
                    print(f"DEBUG - Frontend: Heating exception: {str(e)}")
                    st.error(f'开始加热失败: {str(e)}')
        
        with col2:
            if st.button('停止加热', key=f'heat_stop_{st.session_state.selected_channel}', type='secondary'):
                try:
                    print(f"DEBUG - Frontend: Stopping heating for channel {st.session_state.selected_channel}")
                    response = requests.post(
                        f'{API_BASE}/device/channel/{st.session_state.selected_channel}/control',
                        json={'heating': False}
                    )
                    print(f"DEBUG - Frontend: Stop heating response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print("DEBUG - Frontend: Heating stopped successfully")
                        st.success('停止加热')
                    else:
                        error_detail = response.json().get("detail", "未知错误")
                        print(f"DEBUG - Frontend: Stop heating failed: {error_detail}")
                        st.error(f'停止加热失败: {error_detail}')
                except Exception as e:
                    print(f"DEBUG - Frontend: Stop heating exception: {str(e)}")
                    st.error(f'停止加热失败: {str(e)}')

# 主面板
if st.session_state.connected:
    # 创建占位符
    status_container = st.container()
    chart_container = st.container()
    
    # 实时数据更新
    data = update_data()
    if data:
        with status_container:
            st.subheader('实时状态')
            # 只显示指定数量的通道
            channels = [ch for ch in data.get('channels', []) if ch.get('id', 0) < st.session_state.num_channels]
            
            # 使用网格布局
            cols = st.columns(3)
            for i, channel in enumerate(channels):
                col_idx = i % 3
                with cols[col_idx]:
                    st.metric(
                        f'通道 {channel["id"]}',
                        f'{channel["temperature"]:.1f}°C',
                        f'{channel["temperature"] - channel["pid_params"]["target_temp"]:.1f}°C',
                        label_visibility='visible'
                    )
                    st.metric(
                        '目标温度',
                        f'{channel["pid_params"]["target_temp"]:.1f}°C',
                        delta=None,
                        label_visibility='visible'
                    )
                    st.write('加热状态:', '开启' if channel['heating'] else '关闭')
                    st.write('---')
        
        with chart_container:
            st.header('温度曲线')
            
            # 图表控制
            col1, col2, col3 = st.columns(3)
            with col1:
                # 选择时间范围
                hours = st.slider('显示时间范围(小时)', 0.1, 24.0, 1.0)
            with col2:
                # 选择要显示的通道
                selected_channels = st.multiselect(
                    '选择要显示的通道',
                    range(st.session_state.num_channels),
                    default=list(range(st.session_state.num_channels)),
                    format_func=lambda x: f'通道 {x}'
                )
            with col3:
                # 选择要显示的数据类型
                show_types = st.multiselect(
                    '显示数据类型',
                    ['实际温度', '目标温度'],
                    default=['实际温度', '目标温度']
                )
            
            # 数据导出
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button('导出CSV'):
                    response = requests.get(
                        f'{API_BASE}/device/channel/{st.session_state.selected_channel}/export',
                        params={'hours': hours}
                    )
                    if response.status_code == 200:
                        csv = response.content.decode('utf-8')
                        st.download_button(
                            label='下载CSV文件',
                            data=csv,
                            file_name=f'channel_{st.session_state.selected_channel}_data.csv',
                            mime='text/csv'
                        )
            
            # 获取实时数据并绘制图表
            try:
                if data and st.session_state.data_points:
                    # 创建多通道图表
                    fig = go.Figure()
                    
                    # 设置颜色列表
                    colors = px.colors.qualitative.Set3
                    
                    # 组织数据
                    channel_data = {}
                    for point in st.session_state.data_points:
                        timestamp = datetime.fromisoformat(point['timestamp'])
                        for channel in point['channels']:
                            if channel['id'] not in channel_data:
                                channel_data[channel['id']] = {
                                    'timestamps': [],
                                    'temperatures': [],
                                    'target_temps': []
                                }
                            channel_data[channel['id']]['timestamps'].append(timestamp)
                            channel_data[channel['id']]['temperatures'].append(channel.get('temperature'))
                            channel_data[channel['id']]['target_temps'].append(
                                channel.get('pid_params', {}).get('target_temp')
                            )
                    
                    # 绘制每个通道的温度曲线
                    y_min = float('inf')
                    y_max = float('-inf')
                    
                    for channel_id in selected_channels:
                        if channel_id in channel_data:
                            data = channel_data[channel_id]
                            color = colors[channel_id % len(colors)]
                            
                            # 更新Y轴范围
                            if data['temperatures']:
                                y_min = min(y_min, min(data['temperatures']))
                                y_max = max(y_max, max(data['temperatures']))
                            if data['target_temps']:
                                y_min = min(y_min, min(data['target_temps']))
                                y_max = max(y_max, max(data['target_temps']))
                            
                            # 实际温度
                            if '实际温度' in show_types:
                                fig.add_trace(go.Scatter(
                                    x=data['timestamps'],
                                    y=data['temperatures'],
                                    name=f'通道 {channel_id} 实际温度',
                                    line=dict(color=color),
                                    mode='lines+markers'
                                ))
                            
                            # 目标温度
                            if '目标温度' in show_types:
                                fig.add_trace(go.Scatter(
                                    x=data['timestamps'],
                                    y=data['target_temps'],
                                    name=f'通道 {channel_id} 目标温度',
                                    line=dict(color=color, dash='dash'),
                                    mode='lines'
                                ))
                    
                    if y_min != float('inf') and y_max != float('-inf'):
                        # 添加上下边界的缓冲
                        y_range = y_max - y_min
                        y_min = max(0, y_min - y_range * 0.1)
                        y_max = y_max + y_range * 0.1
                    else:
                        y_min, y_max = 0, 100
                    
                    fig.update_layout(
                        title='多通道温度曲线',
                        xaxis_title='时间',
                        yaxis_title='温度 (℃)',
                        height=500,
                        showlegend=True,
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="right",
                            x=0.99
                        ),
                        yaxis=dict(
                            range=[y_min, y_max]
                        )
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f'获取数据失败: {str(e)}')
    
    # 使用Streamlit的自动刷新功能
    if st.session_state.connected and st.session_state.collecting:
        print(f"DEBUG - Frontend: Auto refresh enabled, counter: {st.session_state.update_counter}")
        time.sleep(st.session_state.update_interval)  # 等待更新间隔
        data = update_data()
        if data:
            print("DEBUG - Frontend: Got new data in auto refresh")
            st.rerun()
