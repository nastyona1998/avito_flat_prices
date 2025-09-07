import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
import time
import sys

def main():
    # Настройка драйвера с отключением прокси
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--headless')
    options.add_argument('--no-proxy-server')
    options.add_argument('--proxy-server="direct://"')
    options.add_argument('--proxy-bypass-list=*')

    driver = webdriver.Chrome(options=options)

    stealth(
        driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    # Список колонок с добавленной "Мебелью" и "Тип продавца"
    columns = [
        'URL', 'Цена', 'Цена за кв.метр', 'Количество собственников', 'Район', 'Улица',
        'Вид сделки', 'Количество комнат', 'Общая площадь', 'Площадь кухни', 'Жилая площадь',
        'Этаж', 'Этажей в доме', 'Балкон или лоджия', 'Высота потолков', 'Санузел', 'Окна', 'Ремонт',
        'Техника', 'Способ продажи', 'Тип дома', 'Год постройки',
        'Пассажирский лифт', 'Грузовой лифт', 'В доме', 'Двор', 'Парковка',
        'Дополнительно', 'Тип комнат', 'Мебель', 'Тип продавца'
    ]

    all_data = []
    descriptions_data = []  # Список для хранения описаний объявлений

    try:
        for page in range(0, 101):  # Парсим первые 2 страницы (начинаем с 1)
            url = f"https://www.avito.ru/samara/kvartiry/prodam?p={page}"
            print(f"Парсим страницу {page}: {url}")

            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-marker='item']"))
                )
                time.sleep(2)

                items = driver.find_elements(By.CSS_SELECTOR, "div[data-marker='item']")
                print(f"Найдено {len(items)} объявлений на странице {page}")

                for i, item in enumerate(items[:]):
                    try:
                        item_url = item.find_element(By.CSS_SELECTOR, "a[data-marker='item-title']").get_attribute('href')
                        print(f"Обрабатываем объявление {i + 1}: {item_url}")

                        driver.execute_script(f"window.open('{item_url}');")
                        driver.switch_to.window(driver.window_handles[1])
                        time.sleep(3)

                        params = {col: None for col in columns}
                        params['URL'] = item_url

                        # Парсинг описания объявления
                        try:
                            description_element = driver.find_element(
                                By.CSS_SELECTOR,
                                "div[data-marker='item-view/item-description']"
                            )
                            description = description_element.text.strip()

                            # Сохраняем описание и URL в отдельный список
                            descriptions_data.append({
                                'URL': item_url,
                                'Описание': description
                            })
                        except Exception as e:
                            print(f"Ошибка при парсинге описания: {str(e)}")
                            descriptions_data.append({
                                'URL': item_url,
                                'Описание': None
                            })

                        # Парсинг цены
                        try:
                            price_element = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
                            params['Цена'] = price_element.get_attribute('content')
                        except Exception as e:
                            print(f"Ошибка при парсинге цены: {str(e)}")

                        # Парсинг цены за кв.метр
                        try:
                            price_per_m2_element = driver.find_element(By.CSS_SELECTOR,
                                                                       "div.styles-item-price-sub-price-A1IZy span")
                            price_per_m2 = price_per_m2_element.text.replace(' ', '').replace('\xa0', '').split('₽')[0]
                            params['Цена за кв.метр'] = price_per_m2
                        except Exception as e:
                            print(f"Ошибка при парсинге цены за кв.метр: {str(e)}")

                        # Парсинг типа продавца (агентство или частное лицо)
                        try:
                            # Проверяем наличие тега с указанием "Частное лицо"
                            try:
                                private_seller = driver.find_element(By.CSS_SELECTOR,
                                                                     "div[data-marker='seller-info/label']")
                                if "частное лицо" in private_seller.text.lower():
                                    params['Тип продавца'] = "частное лицо"
                                else:
                                    params['Тип продавца'] = "агентство"
                            except:
                                # Если нет явной метки, проверяем название продавца
                                seller_name = driver.find_element(By.CSS_SELECTOR,
                                                                  "div[data-marker='seller-info/name']").text
                                if "ооо" in seller_name.lower() or "ао" in seller_name.lower() or "ип" in seller_name.lower():
                                    params['Тип продавца'] = "агентство"
                                else:
                                    params['Тип продавца'] = "частное лицо"
                        except Exception as e:
                            print(f"Ошибка при определении типа продавца: {str(e)}")
                            params['Тип продавца'] = None

                        # ИСПРАВЛЕННЫЙ ПАРСИНГ КОЛИЧЕСТВА СОБСТВЕННИКОВ
                        try:
                            owners_element = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((
                                    By.CSS_SELECTOR,
                                    "div.styles-module-root-Zabz6 p.styles-module-root-o3j6a"
                                ))
                            )
                            owners_text = owners_element.get_attribute('textContent').replace('\xa0', ' ').strip()
                            params['Количество собственников'] = owners_text
                        except Exception as e:
                            print(f"Ошибка при парсинге количества собственников: {str(e)}")
                            params['Количество собственников'] = None

                        # Парсинг адреса
                        try:
                            address = driver.find_element(By.CSS_SELECTOR, "span.style-item-address__string-wt61A").text
                            address_parts = [part.strip() for part in address.split(',')]
                            params['Улица'] = ', '.join(address_parts[-2:]) if len(address_parts) >= 2 else address

                            district = driver.find_element(By.CSS_SELECTOR,
                                                           "span.style-item-address-georeferences-item-TZsrp span").text
                            params['Район'] = district
                        except Exception as e:
                            print(f"Ошибка при парсинге адреса: {str(e)}")

                        # ИСПРАВЛЕННЫЙ ПАРСИНГ ПАРАМЕТРОВ (ВКЛЮЧАЯ МЕБЕЛЬ)
                        try:
                            param_items = driver.find_elements(By.CSS_SELECTOR, "li.params-paramsList__item-_2Y2O")
                            for param in param_items:
                                try:
                                    name_span = param.find_element(By.CSS_SELECTOR, "span.styles-module-noAccent-l9CMS")
                                    name = name_span.text.replace(':', '').strip()

                                    # Удаляем весь HTML названия параметра перед извлечением значения
                                    value = driver.execute_script("""
                                        return arguments[0].innerText.replace(arguments[1], '').replace(':', '').trim();
                                    """, param, name_span.text)

                                    # Словарь для маппинга параметров
                                    param_mapping = {
                                        'Вид сделки': 'Вид сделки',
                                        'Количество комнат': 'Количество комнат',
                                        'Общая площадь': 'Общая площадь',
                                        'Площадь кухни': 'Площадь кухни',
                                        'Жилая площадь': 'Жилая площадь',
                                        'Этаж': 'Этаж',
                                        'Балкон или лоджия': 'Балкон или лоджия',
                                        'Высота потолков': 'Высота потолков',
                                        'Санузел': 'Санузел',
                                        'Окна': 'Окна',
                                        'Ремонт': 'Ремонт',
                                        'Техника': 'Техника',
                                        'Способ продажи': 'Способ продажи',
                                        'Тип дома': 'Тип дома',
                                        'Год постройки': 'Год постройки',
                                        'Пассажирский лифт': 'Пассажирский лифт',
                                        'Грузовой лифт': 'Грузовой лифт',
                                        'В доме': 'В доме',
                                        'Двор': 'Двор',
                                        'Парковка': 'Парковка',
                                        'Дополнительно': 'Дополнительно',
                                        'Тип комнат': 'Тип комнат',
                                        'Мебель': 'Мебель'
                                    }

                                    if name in param_mapping:
                                        if 'площадь' in name.lower() or 'высота' in name.lower():
                                            params[param_mapping[name]] = value.split()[0]
                                        elif name == 'Этаж' and 'из' in value:
                                            floors = value.split('из')
                                            params['Этаж'] = floors[0].strip()
                                            params['Этажей в доме'] = floors[1].strip()
                                        else:
                                            params[param_mapping[name]] = value
                                except Exception as e:
                                    print(f"Ошибка при парсинге параметра: {str(e)}")
                                    continue
                        except Exception as e:
                            print(f"Ошибка при поиске параметров: {str(e)}")

                        all_data.append(params)
                        print(f"Успешно обработано: {item_url}")

                    except Exception as e:
                        print(f"Ошибка при обработке объявления {i + 1}: {str(e)}")
                    finally:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        time.sleep(1)

            except Exception as e:
                print(f"Ошибка при загрузке страницы {page}: {str(e)}")
                continue

        # Сохранение результатов
        if all_data:
            df = pd.DataFrame(all_data)[columns]
            df.to_csv('avito_parsed.csv', index=False, encoding='utf-8-sig')
            print("Парсинг завершен. Результаты сохранены в avito_parsed.csv")
            print(df.head())

            # Сохраняем описания в отдельный файл
            if descriptions_data:
                descriptions_df = pd.DataFrame(descriptions_data)
                descriptions_df.to_csv('avito_descriptions.csv', index=False, encoding='utf-8-sig')
                print("Описания объявлений сохранены в avito_descriptions.csv")
                print(descriptions_df.head())
        else:
            print("Не удалось собрать данные.")

    finally:
        driver.quit()

if __name__ == "__main__":
    print("Запуск парсера Avito...")
    main()
    print("Работа завершена.")
    sys.exit(0)