import json

def convert_cookies_to_json():
    print("""
请按照以下步骤获取知乎cookies：
1. 用Chrome浏览器登录知乎(https://www.zhihu.com)
2. 按F12打开开发者工具
3. 切换到"Network"(网络)标签
4. 刷新页面
5. 在请求列表中找到 www.zhihu.com
6. 在右侧Headers中找到"Cookie:"开头的行
7. 复制整个cookie值（应该是很长的一串，包含多个"名称=值"对，用分号分隔）

请将完整的cookies字符串粘贴在下面（右键粘贴），完成后按回车：
""")
    cookies_str = input().strip()
    
    if not cookies_str:
        print("未输入cookies！")
        return
    
    # 检查输入格式
    if '=' not in cookies_str:
        print("错误：输入的格式不正确！")
        print("正确的cookies应该包含'名称=值'对，例如：")
        print("_zap=xxx; z_c0=yyy; _xsrf=zzz; ...")
        return
    
    # 将cookies字符串转换为字典
    cookies_dict = {}
    for cookie in cookies_str.split(';'):
        if '=' in cookie:
            name, value = cookie.strip().split('=', 1)
            cookies_dict[name.strip()] = value.strip()
    
    if not cookies_dict:
        print("错误：无法解析cookies！")
        return
    
    # 保存为JSON文件
    output_file = 'zhihu_cookies.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cookies_dict, f, ensure_ascii=False, indent=2)
    
    print(f"\nCookies已成功保存到 {output_file}")
    print(f"共保存了 {len(cookies_dict)} 个cookie值")
    print("您现在可以在运行crawler.py时使用这个文件了")

if __name__ == '__main__':
    try:
        convert_cookies_to_json()
    except Exception as e:
        print(f"发生错误: {str(e)}")
        print("请确保输入的cookies格式正确") 