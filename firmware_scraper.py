import requests
from lxml import etree
import os
import urllib.parse
from tqdm import tqdm
import time
from openpyxl import Workbook
import logging
import hashlib



suffixs = ('.jpg', '.png', '.gif','.pdf' ,'.txt' ,'.db','.md5','.lic','.py', '.qcow2', 'ova', 'box')
parent_path = os.path.dirname(os.path.realpath(__file__))
datas = [['固件名称','固件hash','厂商','版本','下载url','固件下载路径']]
#vendor_list = ['Cisco_SDWAN', 'Avaya', 'Misc_Software', 'HP_SERVERS_FW', 'Legacy_Catalysts', '7500', 'Samsung', 'filelist_md5.csv', 'filelist.csv', '7600-6500', 'macOS VMware VMs', '4000', 'PUBLIC_FTP_DIRECTIONS_FOR_THIS_SERVER.txt', '18xx', 'VMware', 'c800-ISR', 'C9800', 'vWLC', 'Nortel-Telephony', 'HP-HPE-ARUBA', 'AS5xxx', '24xx', 'vpn3000', 'MikroTik', 'LiveNX 9.5.0', 'Juniper', '37xx', 'Brocade', '7200', 'Axis', 'upload', 'Wireless', 'ubr7100', '8950', 'Cisco_Collaboration', 'mica', 'Lenovo', 'IGX8400', 'XRv9000', 'Arista', 'IBM_Z_SERIES', '38xx', 'CML', 'Cisco UC520', 'Radio_Software', 'Netapp', 'CIPC', 'PICTURES-FOR-THE-NERDS', 'c8000v', 'powered by h5ai', 'Panasonic PBX', '3CX', 'Panasonic', '120xxXR', 'EVE-NG_IMAGE_PACK', 'ubr920', 'sb101', '3560', '7300', 'soho70', 'C8200_8300_8500_8500L', '36xx', 'C_ISR_4XXX', '4500', 'digium', '7400', 'Nexus', 'Telephony PDFs', 'Fanvil', 'Cisco_Learning_PDF_Videos', '26xx', 'sb107', 'ASR_9XX_1XXX', 'Cisco_Firewall_ASA_FTD', 'CAT3K_9K', 'ubr925', 'iad2430', 'C1100', 'VG_2XX', 'Cisco_Management', '29xx', '16xx', 'Cisco_Phone', 'ubr7200', '8850', 'C9200_9300_9400_9500_9600', '39xx', 'EMC', 'LG', 'Stealthwatch', 'Siemens', '8xx', 'Dell', '19xx', '17xx', '25xx', 'IOSXRdemo', 'CCME', 'soho91', 'modern browsers', '10xx', 'mc3810', 'Adtran', 'CSR1000v', '7100', '67x', 'UC520-8', '28xx', 'soho97', '120xx', 'Microsoft', 'OpenGear', 'RHEL', '10k']
vendor_list = ['Avaya']

# 配置日志记录器
date = time.strftime("%Y%m%d-%H%M%S", time.localtime())
logging.basicConfig(filename='app.log', level=logging.INFO)
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


#下载固件
def firmware_download():
    base_url = 'https://cios.dhitechnical.com/'  # 访问下载链接
    # res = requests.get(base_url,timeout=300)
    # html_tree = etree.HTML(res.text)
    # vendor_list = list(set([a.text for a in html_tree.xpath('//a')])) #获取厂商列表
    for vendor_str in vendor_list:
        vendor_url = f'{base_url}{vendor_str}/'
        vendor_url_res = requests.get(vendor_url ,timeout=300)   #点击厂商,进入厂商页面，获取版本/固件值
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
            print(download_url)
            try:
                download_f_res = requests.get(download_url, stream=True)
                if download_f_res.status_code == 200:
                    total_size = int(download_f_res.headers.get('content-length', 0))
                    progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)
                    with open(f'{file_path}\\{firms}', 'wb') as f:
                        for chunk in download_f_res.iter_content(1024):
                            if chunk:
                                f.write(chunk)
                                progress_bar.update(len(chunk))
                    time.sleep(2)
                    progress_bar.close()
                    url_hash = Get_file_md5(f'{file_path}\\{firms}')
                    ll = (firms, url_hash, vendor_str, '/', processed_url, f'{file_path}\\{firms}')
                    data = list(ll)
                    datas.append(data)
                    save_logs(f"{download_url}  下载成功")
                else:
                    save_logs(f"======something wrong======: {download_url}下载失败")
                    import traceback
                    traceback.print_exc()
            except requests.exceptions.RequestException as e:
                save_logs(f'请求错误:{e}')
            except FileNotFoundError as e:  # 处理文件写入错误
                save_logs(f'文件写入错误:{e}')

        exists_floder = v_html_tree.xpath('count(//img[@alt="folder"]) > 0')  #判断是否存在版本页面
        if exists_floder == True:  #如果存在固件版本，则继续点击版本，进入固件页面
            version_name = list(set([vendorname.text for vendorname in v_html_tree.xpath('//img[@alt="folder"]/../..//a')])) #返回所有版本名字
            for version in version_name:
                p_url = f'{vendor_url}{version}/'
                firmware_url = urllib.parse.quote(p_url, safe='/:?&=')
                firmware_name_res = requests.get(firmware_url, timeout=300 )  #继续点击版本，进入固件页面
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
                        print(f_download_url)
                        try:
                            download_firm_res = requests.get(f_download_url , stream=True)  # 点击下载固件
                            if download_firm_res.status_code == 200:
                                total_size = int(download_firm_res.headers.get('content-length', 0))
                                progress_bar = tqdm(total=total_size, unit='B', unit_scale=True)
                                with open(f'{file_path}\\{firm}', 'wb') as f:
                                    for chunk in download_firm_res.iter_content(1024):
                                        if chunk:
                                            f.write(chunk)
                                            progress_bar.update(len(chunk))
                                time.sleep(2)
                                progress_bar.close()
                                url_hash = Get_file_md5(f'{file_path}\\{firm}')
                                ll = (firm, url_hash, vendor_str, version, f'{p_url}{firm}', f'{file_path}\\{firm}')
                                data = list(ll)
                                datas.append(data)
                                save_logs(f"{f_download_url}  下载成功")
                            else:
                                save_logs(f"=============something wrong:{f_download_url}下载失败")
                                import traceback
                                traceback.print_exc()

                        except requests.exceptions.RequestException as e:
                            save_logs(f'请求错误:{e}')
                        except FileNotFoundError as e:  # 处理文件写入错误
                            save_logs(f'文件写入错误:{e}')
                else:
                    continue
    Excel_Create(datas)




if __name__ == '__main__':
    firmware_download()
