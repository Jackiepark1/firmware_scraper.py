from lxml import etree
import urllib.parse
import time
from openpyxl import Workbook
import os
import hashlib
import logging
import requests
import traceback
from contextlib import closing
from tqdm import tqdm



suffixs = ('.jpg', '.png', '.gif','.pdf' ,'.txt' ,'.db','.md5','.lic','.py', '.qcow2', 'ova', 'box')
parent_path = os.path.dirname(os.path.realpath(__file__))
vendor_list = ['3CX']
datas = [['固件名称','固件hash','厂商','版本','下载url','固件下载路径']]
ll1 = []
ll2 = []

# 配置日志记录器
date = time.strftime("%Y%m%d-%H%M%S", time.localtime())
logging.basicConfig(filename='firmware_download{}.log'.format(date), level=logging.INFO)
logger = logging.getLogger()

def save_logs(log):
    try:
        # 将日志写入文件中
        with open('firmware_download{}.log'.format(date), 'a') as file:
            file.write(f"{log}\n")
    except Exception as e:
        logger.error(f"无法保存日志至文件：{e}")


#创建excel表格
def Excel_Create(data):
    # 创建一个叫wk的excel表格
    wk = Workbook()
    # 选择第一个工作表
    sheet = wk.active
    date = time.strftime("%Y%m%d-%H%M%S",time.localtime())
    for row in data:
        sheet.append(row)
    wk.save('C:\\Users\\anban\\Desktop\\固件下载记录{}.xlsx'.format(date))
    wk.close()



#获取hash值
def Get_file_md5(file_path):
    try:
        with open(file_path,'rb') as f:
            md5obj = hashlib.md5()
            md5obj.update(f.read())
            hash_value = md5obj.hexdigest()
            return hash_value
    except Exception as e:
        print('ERROR', f'获取文件{file_path}md5值出错,原因{e}')
        return False



def breakpoint_download_file(file_url, file_dir, new_file_name):
    """断点续传下载文件"""
    save_logs(f"Start breakpoint download file, file_url: {file_url}")
    print(file_url)
    try:
        os.mkdir(file_dir)
    except FileExistsError:
        pass
    except FileNotFoundError:
        os.makedirs(file_dir)

    # 设置 headers，检查文件下载进度
    file_path = file_dir + new_file_name
    if os.path.exists(file_path):
        start_byte = os.path.getsize(file_path)
    else:
        start_byte = 0
    headers = {'Content-Range': f'bytes={start_byte}-'}  #Range


    # 发送 GET 请求
    try:
        with closing(requests.get(url=file_url, stream=True, headers=headers)) as res:
            # 206表示该服务器已经成功处理了部分 GET 请求
            if res.status_code not in [200, 206]:
                return -1, None, res.text

            # 获取总字节数，计算出剩余未下载的字节数
            total_size = int(res.headers.get('Content-Length', 0))  #content-length
            remaining_bytes = total_size - start_byte
            progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)


            # 写入文件
            with open(file_path, 'ab') as f:
                for chunk in res.iter_content(chunk_size=1024):
                    # 如果已经下载完成，退出循环
                    if remaining_bytes <= 0:
                        save_logs(f"{file_path}  文件已存在，跳过下载")
                        break

                    # 计算本次需要写入的字节数
                    bytes_to_write = len(chunk)
                    if bytes_to_write > remaining_bytes:
                        bytes_to_write = remaining_bytes

                    # 写入文件并更新记录
                    f.write(chunk[:bytes_to_write])
                    remaining_bytes -= bytes_to_write

                    progress_bar.update(len(chunk))
            progress_bar.close()

        # 以二进制只读方式打开文件并计算 MD5 校验和
        # 以二进制只读方式打开文件并计算 MD5 校验和
        with open(file_path, 'rb') as f:
            md5_hash = hashlib.md5()
            chunk = f.read(8192)
            while chunk:
                md5_hash.update(chunk)
                chunk = f.read(8192)

        save_logs(f"End to download file, url: {file_url}, filepath: {file_path}, "
                    f"filesize: {os.path.getsize(file_path)}, md5: {md5_hash.hexdigest()}")
        return 0, md5_hash.hexdigest(), "Success"
    except Exception as e:
        logger.error(traceback.format_exc())
        return -1, None, str(e)




#下载固件
def firmware_download():
    base_url = 'https://cios.dhitechnical.com/'  # 访问下载链接
    # res = requests.get(base_url,timeout=100)
    # html_tree = etree.HTML(res.text)
    # vendor_list = list(set([a.text for a in html_tree.xpath('//a')])) #获取厂商列表
    for vendor_str in vendor_list:
        vendor_url = f'{base_url}{vendor_str}/'
        vendor_url_res = requests.get(vendor_url ,timeout=100)   #点击厂商,进入厂商页面，获取版本/固件值
        v_html_tree = etree.HTML(vendor_url_res.text)

        f_name = list(set([filename.text for filename in v_html_tree.xpath('//img[@alt="file"]/../..//a')]))
        filtered_list = [item for item in f_name if not item.endswith(suffixs)]
        for firms in filtered_list:
            file_path = f'{parent_path}\\{vendor_str}'
            isExists = os.path.exists(file_path)
            if not isExists:
                os.makedirs(file_path)
            processed_url = f'{vendor_url}{firms}'
            download_url = processed_url.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
            try:
                breakpoint_download_file(file_url=download_url,
                                        file_dir=f'{file_path}\\',
                                         new_file_name=firms)
                url_hash = Get_file_md5(f'{file_path}\\{firms}')
                ll = (firms, url_hash, vendor_str, '/', processed_url, f'{file_path}\\{firms}')
                data = list(ll)
                datas.append(data)
                save_logs(f"{download_url}  下载成功")
            except:
                save_logs(f"======something wrong======: {download_url}下载失败")
                import traceback
                traceback.print_exc()


        exists_floder = v_html_tree.xpath('count(//img[@alt="folder"]) > 0')  #判断是否存在版本页面
        if exists_floder == True:  #如果存在固件版本，则继续点击版本，进入固件页面
            version_name = list(set([vendorname.text for vendorname in v_html_tree.xpath('//img[@alt="folder"]/../..//a')])) #返回所有版本名字
            for version in version_name:
                p_url = f'{vendor_url}{version}/'
                firmware_url = urllib.parse.quote(p_url, safe='/:?&=')
                firmware_name_res = requests.get(firmware_url)  #继续点击版本，进入固件页面
                if firmware_name_res.status_code == 200:   # 如果页面不能访问就跳过
                    file_html_tree = etree.HTML(firmware_name_res.text)
                    firm_name = list(set([firmname.text for firmname in file_html_tree.xpath('//img[@alt="file"]/../..//a')])) #获取所有固件的名字列表
                    filtered_list = [item for item in firm_name if not item.endswith(suffixs)]
                    file_path = f'{parent_path}\\{vendor_str}\\{version}'
                    isExists = os.path.exists(file_path)
                    if not isExists:
                        os.makedirs(file_path)
                    for firm in filtered_list:
                        d_url = f'{firmware_url}{firm}'   #固件下载url
                        f_download_url = d_url.replace(' ', '%20').replace('(', '%28').replace(')', '%29')
                        try:
                            breakpoint_download_file(file_url=f_download_url,
                                                     file_dir=f'{file_path}\\',
                                                     new_file_name=firm)
                            url_hash = Get_file_md5(f'{file_path}\\{firm}')
                            ll = (firm, url_hash, vendor_str, version, f'{p_url}{firm}', f'{file_path}\\{firm}')
                            data = list(ll)
                            datas.append(data)
                            save_logs(f"{f_download_url}  下载成功")
                        except:
                            save_logs(f"=============something wrong:{f_download_url}下载失败")
                            import traceback
                            traceback.print_exc()
                else:
                    continue
    Excel_Create(datas)




if __name__ == '__main__':
    firmware_download()

