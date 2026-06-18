"""
荟城减重 WSP 系统 - 端到端测试脚本
覆盖所有关键场景和边界条件
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = 'http://127.0.0.1:5000'

def log(test_name, status, message=''):
    """打印测试结果"""
    icon = '✅' if status else '❌'
    print(f"\n{icon} {test_name}")
    if message:
        print(f"   {message}")

def test_dashboard():
    """测试仪表盘API"""
    print("\n" + "="*60)
    print("测试1: 仪表盘数据")
    print("="*60)
    
    try:
        response = requests.get(f'{BASE_URL}/api/dashboard')
        data = response.json()
        
        # 验证返回数据结构
        required_fields = ['today_count', 'pending', 'completed', 'blocked', 'recent', 'trend']
        missing = [f for f in required_fields if f not in data]
        
        if missing:
            log('仪表盘数据结构', False, f'缺少字段: {missing}')
            return False
        
        # 验证趋势数据
        if data['trend']:
            # 检查是否按日期排序
            dates = [t['date'] for t in data['trend']]
            is_sorted = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
            log('趋势数据排序', is_sorted, f'共{len(dates)}天数据' if is_sorted else '数据未排序!')
            
            # 检查是否有7天数据
            log('趋势数据完整性', len(data['trend']) == 7, f'实际{len(data["trend"])}天,期望7天')
            
            # 检查每个数据点是否有count字段
            has_count = all('count' in t for t in data['trend'])
            log('趋势数据count字段', has_count)
        else:
            log('趋势数据', True, '暂无数据(正常)')
        
        log('仪表盘API', True, f'今日:{data["today_count"]}, 待生成:{data["pending"]}, 已完成:{data["completed"]}, 阻断:{data["blocked"]}')
        return True
        
    except Exception as e:
        log('仪表盘API', False, str(e))
        return False

def test_create_report_valid():
    """测试创建报告 - 正常数据"""
    print("\n" + "="*60)
    print("测试2: 创建报告 - 正常数据")
    print("="*60)
    
    report_data = {
        'name': '测试用户A',
        'sex': '男',
        'age': 35,
        'phone': '13800138000',
        'occupation_status': '久坐办公',
        'height_cm': 175,
        'weight_kg': 80,
        'waist_cm': 90,
        'hip_cm': 100,
        'sbp': 130,
        'dbp': 85,
        'heart_rate': 75,
        'body_fat_percent': 25,
        'visceral_fat_level': 8,
        'target_weight_kg': 70,
        'target_waist_cm': 85,
        'past_weight_loss': '成功过但反弹',
        'eating_out_frequency': '每周1-2次',
        'night_snack_sweet_drink': '每周1-2次',
        'staple_oily_food': '主食偏多',
        'exercise_frequency': '每周1-2次',
        'sleep_status': '偶尔熬夜',
        'bowel_status': '1-2天一次',
        'stress_eating': '偶尔',
        'water_intake': '一般',
        'suitable_path': '全程版',
        'report_focus_note': '测试备注',
        'female_status': None,
        'tongue_photo_taken': '已拍',
        'med_detail': '',
        'selected_goals': ['减重', '减腰围'],
        'selected_gain_reasons': ['久坐', '外卖/夜宵'],
        'conditions': [],
        'medications': [],
        'allergies': [],
        'red_positive': [],
        'body_feelings': ['疲劳'],
        'tcm_tendency': ['痰湿质'],
        'main_obstacles': ['久坐不动'],
        'external_cautions': ['无禁忌'],
        'risk_scores': {
            '代谢风险': 2,
            '心血管风险': 2,
            '执行难度': 2,
            '反弹风险': 2
        }
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/reports', json=report_data)
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            log('创建报告(正常)', True, f'报告ID: {result["record_id"]}, 状态: {result["status"]}')
            return result['record_id']
        else:
            log('创建报告(正常)', False, result.get('error', '未知错误'))
            return None
            
    except Exception as e:
        log('创建报告(正常)', False, str(e))
        return None

def test_create_report_boundary_values():
    """测试创建报告 - 边界值"""
    print("\n" + "="*60)
    print("测试3: 创建报告 - 边界值验证")
    print("="*60)
    
    test_cases = [
        ('身高最小值', {'height_cm': 100, 'weight_kg': 50, 'target_weight_kg': 45}, True),
        ('身高最大值', {'height_cm': 250, 'weight_kg': 100, 'target_weight_kg': 90}, True),
        ('身高超限', {'height_cm': 251, 'weight_kg': 50, 'target_weight_kg': 45}, False),
        ('体重最小值', {'height_cm': 170, 'weight_kg': 30, 'target_weight_kg': 28}, True),
        ('体重最大值', {'height_cm': 170, 'weight_kg': 300, 'target_weight_kg': 280}, True),
        ('体重超限', {'height_cm': 170, 'weight_kg': 301, 'target_weight_kg': 280}, False),
        ('收缩压边界', {'height_cm': 170, 'weight_kg': 70, 'sbp': 250}, True),
        ('收缩压超限', {'height_cm': 170, 'weight_kg': 70, 'sbp': 251}, False),
        ('舒张压边界', {'height_cm': 170, 'weight_kg': 70, 'dbp': 150}, True),
        ('舒张压超限', {'height_cm': 170, 'weight_kg': 70, 'dbp': 151}, False),
        ('心率边界低', {'height_cm': 170, 'weight_kg': 70, 'heart_rate': 40}, True),
        ('心率边界高', {'height_cm': 170, 'weight_kg': 70, 'heart_rate': 200}, True),
        ('心率超限', {'height_cm': 170, 'weight_kg': 70, 'heart_rate': 201}, False),
        ('体脂率边界', {'height_cm': 170, 'weight_kg': 70, 'body_fat_percent': 5}, True),
        ('体脂率超限', {'height_cm': 170, 'weight_kg': 70, 'body_fat_percent': 61}, False),
        ('内脏脂肪边界', {'height_cm': 170, 'weight_kg': 70, 'visceral_fat_level': 1}, True),
        ('内脏脂肪超限', {'height_cm': 170, 'weight_kg': 70, 'visceral_fat_level': 60}, False),
    ]
    
    passed = 0
    failed = 0
    
    for name, extra_data, should_pass in test_cases:
        base_data = {
            'name': f'边界测试-{name}',
            'sex': '男',
            'age': 30,
            'phone': '13800138000',
            'height_cm': 170,
            'weight_kg': 70,
            'waist_cm': 85,
            'hip_cm': 95,
            'target_weight_kg': 65,
            'target_waist_cm': 80,
            'past_weight_loss': '从未减过',
            'eating_out_frequency': '几乎不外食',
            'night_snack_sweet_drink': '基本不吃',
            'staple_oily_food': '主食适量、清淡',
            'exercise_frequency': '每天运动',
            'sleep_status': '早睡早起',
            'bowel_status': '每天1-2次',
            'stress_eating': '不明显',
            'water_intake': '充足（≥2000ml）',
            'suitable_path': '全程版',
            'selected_goals': ['减重'],
            'selected_gain_reasons': ['久坐'],
            'conditions': [],
            'medications': [],
            'allergies': [],
            'red_positive': [],
            'body_feelings': [],
            'tcm_tendency': ['痰湿质'],
            'main_obstacles': [],
            'external_cautions': ['无禁忌'],
            'risk_scores': {'代谢风险': 2, '心血管风险': 2, '执行难度': 2, '反弹风险': 2}
        }
        base_data.update(extra_data)
        
        try:
            response = requests.post(f'{BASE_URL}/api/reports', json=base_data)
            result = response.json()
            
            if should_pass:
                if response.status_code == 200 and result.get('success'):
                    log(f'{name}', True, '通过验证')
                    passed += 1
                else:
                    log(f'{name}', False, f'应该通过但失败: {result.get("error")}')
                    failed += 1
            else:
                if response.status_code == 400:
                    log(f'{name}', True, f'正确拦截: {result.get("error")}')
                    passed += 1
                else:
                    log(f'{name}', False, '应该拦截但未拦截')
                    failed += 1
                    
        except Exception as e:
            log(f'{name}', False, str(e))
            failed += 1
    
    print(f"\n边界值测试总结: 通过{passed}, 失败{failed}")
    return failed == 0

def test_create_report_string_numbers():
    """测试字符串类型的数值(前端常见情况)"""
    print("\n" + "="*60)
    print("测试4: 创建报告 - 字符串数值转换")
    print("="*60)
    
    report_data = {
        'name': '字符串数值测试',
        'sex': '女',
        'age': '28',  # 字符串
        'phone': '13900139000',
        'height_cm': '165',  # 字符串
        'weight_kg': '60',  # 字符串
        'waist_cm': '80',  # 字符串
        'hip_cm': '95',  # 字符串
        'sbp': '120',  # 字符串
        'dbp': '80',  # 字符串
        'heart_rate': '72',  # 字符串
        'body_fat_percent': '22.5',  # 字符串浮点数
        'visceral_fat_level': '6',  # 字符串整数
        'target_weight_kg': '55',  # 字符串
        'target_waist_cm': '75',  # 字符串
        'past_weight_loss': '尝试过没效果',
        'eating_out_frequency': '每周1-2次',
        'night_snack_sweet_drink': '每周1-2次',
        'staple_oily_food': '主食偏多',
        'exercise_frequency': '每周3-5次',
        'sleep_status': '偶尔熬夜',
        'bowel_status': '1-2天一次',
        'stress_eating': '偶尔',
        'water_intake': '一般',
        'suitable_path': '轻享版',
        'selected_goals': ['减重', '降体脂'],
        'selected_gain_reasons': ['压力大'],
        'conditions': [],
        'medications': [],
        'allergies': [],
        'red_positive': [],
        'body_feelings': ['怕冷'],
        'tcm_tendency': ['阳虚质'],
        'main_obstacles': ['睡眠不足'],
        'external_cautions': ['无禁忌'],
        'risk_scores': {'代谢风险': 2, '心血管风险': 1, '执行难度': 2, '反弹风险': 3}
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/reports', json=report_data)
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            log('字符串数值转换', True, f'成功处理字符串类型数值, 报告ID: {result["record_id"]}')
            return result['record_id']
        else:
            log('字符串数值转换', False, result.get('error', '未知错误'))
            return None
            
    except Exception as e:
        log('字符串数值转换', False, str(e))
        import traceback
        traceback.print_exc()
        return None

def test_generate_report(record_id):
    """测试报告生成"""
    print("\n" + "="*60)
    print("测试5: 报告生成")
    print("="*60)
    
    if not record_id:
        log('报告生成', False, '没有可用的报告ID')
        return False
    
    try:
        response = requests.post(f'{BASE_URL}/api/reports/{record_id}/generate')
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            log('报告生成', True, f'状态: {result["status"]}, 闸门: {result.get("gate_status")}')
            
            # 验证报告详情
            detail_response = requests.get(f'{BASE_URL}/api/reports/{record_id}')
            detail = detail_response.json()
            
            has_content = bool(detail.get('content'))
            has_md = bool(detail.get('md_content'))
            log('PDF内容生成', has_content)
            log('MD内容生成', has_md)
            
            return has_content and has_md
        else:
            log('报告生成', False, result.get('error', '未知错误'))
            return False
            
    except Exception as e:
        log('报告生成', False, str(e))
        import traceback
        traceback.print_exc()
        return False

def test_gate_logic():
    """测试闸门逻辑"""
    print("\n" + "="*60)
    print("测试6: 闸门逻辑")
    print("="*60)
    
    # 测试红旗项阻断
    blocked_data = {
        'name': '红旗项测试',
        'sex': '男',
        'age': 45,
        'phone': '13700137000',
        'height_cm': 170,
        'weight_kg': 85,
        'waist_cm': 95,
        'hip_cm': 100,
        'target_weight_kg': 75,
        'target_waist_cm': 88,
        'past_weight_loss': '从未减过',
        'eating_out_frequency': '几乎每天外食',
        'night_snack_sweet_drink': '几乎每天',
        'staple_oily_food': '两者都偏多',
        'exercise_frequency': '很少运动',
        'sleep_status': '经常熬夜',
        'bowel_status': '3天以上一次',
        'stress_eating': '非常明显',
        'water_intake': '很少喝水',
        'suitable_path': '全程版',
        'selected_goals': ['减重'],
        'selected_gain_reasons': ['饮酒'],
        'conditions': ['高血压'],
        'medications': ['降压药'],
        'allergies': [],
        'red_positive': ['胸痛胸闷', '血压严重异常'],  # 红旗项
        'body_feelings': ['疲劳', '水肿'],
        'tcm_tendency': ['痰湿质', '血瘀质'],
        'main_obstacles': ['热量摄入', '久坐不动'],
        'external_cautions': ['血压禁忌'],
        'risk_scores': {'代谢风险': 5, '心血管风险': 5, '执行难度': 4, '反弹风险': 4}
    }
    
    try:
        response = requests.post(f'{BASE_URL}/api/reports', json=blocked_data)
        result = response.json()
        
        if response.status_code == 200 and result.get('success'):
            is_blocked = result['status'] == 'blocked'
            log('红旗项阻断', is_blocked, f'状态: {result["status"]}, 原因: {result.get("gate_reason")}')
            
            # 检查闸门日志
            logs_response = requests.get(f'{BASE_URL}/api/reports/{result["record_id"]}/gate-logs')
            logs = logs_response.json()
            has_block_log = any(log['gate_status'] == 'block' for log in logs)
            log('闸门日志记录', has_block_log, f'共{len(logs)}条日志')
            
            return is_blocked and has_block_log
        else:
            log('红旗项阻断', False, result.get('error', '未知错误'))
            return False
            
    except Exception as e:
        log('红旗项阻断', False, str(e))
        return False

def test_report_list_and_search():
    """测试报告列表和搜索"""
    print("\n" + "="*60)
    print("测试7: 报告列表和搜索")
    print("="*60)
    
    try:
        # 获取全部报告
        response = requests.get(f'{BASE_URL}/api/reports')
        reports = response.json()
        log('获取报告列表', True, f'共{len(reports)}条报告')
        
        # 测试搜索
        search_response = requests.get(f'{BASE_URL}/api/reports?keyword=测试')
        search_results = search_response.json()
        log('关键词搜索', True, f'找到{len(search_results)}条')
        
        # 测试状态过滤
        completed_response = requests.get(f'{BASE_URL}/api/reports?status=completed')
        completed = completed_response.json()
        log('状态过滤(completed)', True, f'找到{len(completed)}条')
        
        blocked_response = requests.get(f'{BASE_URL}/api/reports?status=blocked')
        blocked = blocked_response.json()
        log('状态过滤(blocked)', True, f'找到{len(blocked)}条')
        
        return True
        
    except Exception as e:
        log('报告列表和搜索', False, str(e))
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("# 荟城减重 WSP 系统 - 端到端测试")
    print("#"*60)
    
    results = {}
    
    # 测试1: 仪表盘
    results['dashboard'] = test_dashboard()
    
    # 测试2: 创建报告(正常)
    normal_record_id = test_create_report_valid()
    results['create_normal'] = normal_record_id is not None
    
    # 测试3: 边界值验证
    results['boundary_values'] = test_create_report_boundary_values()
    
    # 测试4: 字符串数值转换
    string_record_id = test_create_report_string_numbers()
    results['string_conversion'] = string_record_id is not None
    
    # 测试5: 报告生成
    if normal_record_id:
        results['generate_report'] = test_generate_report(normal_record_id)
    else:
        results['generate_report'] = False
    
    # 测试6: 闸门逻辑
    results['gate_logic'] = test_gate_logic()
    
    # 测试7: 报告列表和搜索
    results['list_and_search'] = test_report_list_and_search()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        icon = '✅' if result else '❌'
        print(f"{icon} {test_name}: {'通过' if result else '失败'}")
    
    print(f"\n总计: {total}个测试, 通过{passed}, 失败{failed}")
    
    if failed > 0:
        print("\n⚠️  存在失败的测试,请检查上述错误信息!")
        return False
    else:
        print("\n🎉 所有测试通过!")
        return True

if __name__ == '__main__':
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
