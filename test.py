# #итерация по строке
# auto = "toyota"
# for govno2 in range (1, 4):
#     print(govno2)

# #цикл с условием
# count = 9
# while count < 10:
#         print("ЕСТЬ КОНТАКТ")
#         count += 1
# #цикл с условием и оператором break

# count = 8
# while count < 20:
#       print("ЕСТЬ ВТОРОЙ КОНТАКТ")
#       count += 1
#       if count == 10:
#                print("КОНТАКТ ПРОПАЛ")
#                break

# #цикл с условием и оператором if и else и elif
# count = int(input("Введите число: "))
# if count > 20:
#    print("ЕСТЬ ТРЕТИЙ КОНТАКТ")
# elif count == 20:
#     print("КОНТАКТ НА ГРАНИ")
# elif count < 20:
#     print("КОНТАКТ ПРОПАЛ")
# else:
#     print("КОНТАКТ ПРОПАЛ")
# #continue в цикле for
# for i in range(1, 10):
#     if i == 5:
#         continue
#     print(i)

# условие для continue в цикле for и % для определения кратности
# for i in range(1, 31):
#     if i % 2 == 0:
#         continue
#     else:
#         print(i)

# #оператор in для проверки наличия подстроки в строке
# name = "Artem"
# print("Arho" in name) 
# print("Artem" not in name)

# Индексация строк
# auto = "toyota"
# print(auto[0])
# print(auto[1])     
# print(auto[-1])
# print(auto[-2])
# print(auto[0:3])
# print(auto[0:7])
# print(auto[0:-2])
# print(auto[0:7:2])
# print(auto[::2])

# #len() для определения длины строки
# auto = "toyota"
# print(len(auto))

# # методы строк
# Auto = "toyoTa"
# Auto = Auto.strip()
# print(len(Auto))
# print(Auto.lower())
# print(Auto.upper()) 
# print(Auto.capitalize())
# print(Auto.title())
# print(Auto.startswith("t"))
# print(Auto.endswith("a"))
# print(Auto.count("0"))
# Auto = Auto.replace("o", "0")
# print(Auto)
# print(Auto.count("0"))

#переменная f для форматирования строк
# name = "Artem"
# age = 17
# print(f"Меня зовут {name} и мне {age} лет") 

# name = "Ivan"
# age = 18
# print("меня зовут " + name + " и мне " + str(age) + " лет")

# Проверка на пустую строку и наличие слова SPAM в строке
# n = "message"
# n = n.strip()
# n = n.upper()
# if len(n) == 0:
#     print("EMPTY")
# elif "SPAM" in n:
#     print("BLOCKED")
# else:
# #     print("ALLOWED")


# # full_name = input("Введите ваше имя и фамилию: ")
# # full_name = full_name.strip()
# # full_name = full_name.capitalize()
# # print (f"{full_name[0]}.{full_name[-1]}")
# # список - это изменяемый тип данных, который может содержать элементы разных типов данных
# # l = ["Ivan", "Artem", 17, 1.75, True]
# # # # print(l)
# # # # print(l[0])
# # # # print(len(l))
# # # # print(l[0:3])
# # # # print(range(len(l)))
# # new_list = [1, 2, 3, 4, 5]
# # # print(new_list)
# # # print(min(new_list))
# # # print(max(new_list))
# # # print(sum(new_list))
# # print(new_list[0] + new_list[1])
# # print (max(l))
# # new_list.append(6)
# # print(new_list)
# # new_list.insert(0, 0)
# # print(new_list)
# # new_list.remove(3)
# # print(new_list)
# # deletet = new_list.pop(0)
# # print(f"Удаленный элемент: {deletet}")
# # new_list.clear()
# # print(new_list)
# # new_list.sort(reverse=True)
# # print(new_list)

# # # for i in new_list:
# # #     print(i)    
# # # for index , element in enumerate(new_list):
# # #      print(f"Индекс: {index}, элемент: {element}")

# # string = "Hello, World! Welcome to Python programming."
# # # my_list = string.split()
# # # print(my_list)
# # ip = "127.0.0.1"
# # print (ip.split("."))
# # string = " ".join(ip)
# # print(string)

# # zalupka = [i for i in range(1, 6) if i != 5]
# # print(zalupka)


# # numbers = [12, 5, 8, 99, 3, 8]
# # # print (numbers[0], numbers[-1])
# # # print (8 in numbers)
# # print(max(numbers))
# # print(min(numbers))
# # print(sum(numbers))

# # gods = ['Zeus', 'Apollo', 'Ares']
# # gods.append('Hermes')
# # gods.insert(1, 'Hades')
# # gods.remove('Apollo')
# # diesgods = gods.pop(-1)
# # print(f"Удаленные боги: {diesgods}" " | " "Остальные боги: {gods}" )

# numbers = [4, 7, 10, 15, 18, 21, 24]
# # for i in numbers:
# #     print(i)
# # for i in numbers:
# #     if i % 2 == 0:
# #         print(i)
# # count = 0
# # for i in numbers:
# #     if i > 10:
# #         count += 1
# # else:    print(f"Количество чисел больше 10: {count}")
# # count = 0
# # for i in numbers:
# #     if i > 10:
# #         count += 1
# # print(f"Количество чисел больше 10: {count}")

# # text = input("Введите текст: ")
# # text = text.split()
# # print (text)
# # text = "-".join(text)
# # print(text)

# NUMBERS = [i * i for i in range(1, 11) if i * i % 3 != 0]
# print(NUMBERS)

# author = {
#     "name": "Artem",
#     "age": 24,
#     "student": True
# }
# # print(author["name"])
# # print(author["age"])
# # print(author["student"])
# # print(author)
# # print(author.get("city", "kharkov"))
# # for key in author:
# #     print(f"{key}: {author[key]}")
# # for pair in author.keys():
# #     print(pair)
# # for pair in author.items():
# # #     print(pair)
# # for key, value in author.items():
# #     print(f"{key}: {value}")
# Artem = author = {
#     "name": "Artem",
#     "age": 24,
# #     "student": True,
# #     "city": "Kharkov"
# }
# author.get("suername", "Kuznetsov")
# author["city"] = "Krakov"
# author["learning_python"] = True
# author.pop("city")
# for key, value in author.items():
#     print(f"{key}: {value}")
# wallet = {"USD": 100, "EUR": 150}
# total_eur = 0  # Сюда будем складывать бабки

# for currency, amount in wallet.items():
#     if currency == "USD":
#         total_eur += amount * 0.9  # Переводим баксы в евро и плюсуем
#     else:
#         total_eur += amount        # Евро просто плюсуем как есть

# print(f"Общая сумма в кошельке: {total_eur} EUR")