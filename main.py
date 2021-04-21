import pdfplumber

FILE_NAME = 'External_abdula.pdf'
FILE_PATH = f"pdf/{FILE_NAME}"


def find_name(pdf):
    first_page = pdf.pages[0]
    lines = first_page.lines
    header = first_page.crop((lines[0].get('x0'), (lines[0].get('top')), lines[0].get('x1'), (lines[0].get('bottom') + 100))) # Имя/Фамилия
    header_chars = header.chars
    result_name = ""
    for char in header_chars:
        if char.get('text') == '(':
            break
        result_name += char.get('text')
    return result_name


def find_gender(pdf):
    first_page = pdf.pages[0]
    lines = first_page.lines
    gender_block = first_page.crop(((lines[1].get('x0') + 120), (lines[1].get('top') + 40), (lines[1].get('x1') - 300),
                                      (lines[1].get('bottom') + 80)))  # Имя/Фамилия
    # im = gender_block.to_image(resolution=150)
    # im.save('gender.png', format="PNG")
    text = gender_block.extract_text().split('\n')
    return text[1]


def detect_text_to_block(field, block):
    words = block.extract_words(use_text_flow=True, keep_blank_chars=True)
    for word in words:
        text = word.get('text')
        if text.find(field) != -1:
            return text.replace(field, "")


def find_text_in_document(pdf):
    education_fields = ['Education/Qualification/Training', 'Start Date', 'Field of study', 'Education (degree)',
                        'Training completed', 'Relevant training completed']
    person_name = detect_text_to_block('First Name', pdf.pages[0])
    person_last_name = detect_text_to_block('Family/Last Name', pdf.pages[0])
    gender = detect_text_to_block('Gender', pdf.pages[0])
    educations = []
    education_blocks = find_education(pdf)
    for block in education_blocks:
        education_component = {}
        for education_field in education_fields:
            detected_text = detect_text_to_block(education_field, block)
            if detected_text:
                education_component[education_field] = detected_text
        if education_component:
            educations.append(education_component)
    return {'person_name': person_name, 'person_last_name': person_last_name, 'gender': gender, 'education': educations}


def find_education(pdf):
    education_text = 'Education, Qualification and Training'
    work_exp_text = 'Work Experience'
    education_block_start = {}
    education_block_end = {}
    count_start = 0
    count_end = 0
    for page in pdf.pages:
        lines = page.lines
        for line in lines:
            x0 = line.get('x0')
            top = line.get('top') - 20
            x1 = line.get('x1') + 1
            bottom = line.get('bottom')
            education_block = page.crop((x0, top, x1, bottom))
            try:
                text = education_block.extract_text().replace('\n', ' ')
                if text == education_text:
                    count_start += 1
                    education_block_start = {'x0': x0, 'y0': top + 20, 'x1': x1, 'y1': bottom,
                                             'page_number': page.page_number}
                elif text == work_exp_text:
                    count_end += 1
                    education_block_end = {'x0': x0, 'y0': top, 'x1': x1, 'y1': bottom - 20,
                                           'page_number': page.page_number, 'isLast': True}
            except Exception:
                pass
    education_pages = [*range(education_block_start.get('page_number') - 1, education_block_end.get('page_number'))]
    # Чертим мнимые линии
    imaginary_lines = {}
    for ed_page in education_pages:
        page = pdf.pages[ed_page]
        imaginary_lines[f'{ed_page}'] = []
        for line in page.lines:
            if ed_page == education_block_end.get('page_number') - 1:
                if education_block_end.get('y0') > line.get('top') and line.get('x0') > education_block_start.get('x0') + 10:
                    imaginary_lines[f'{ed_page}'].append({'x0': education_block_start.get('x0'), 'y0': line.get('top'),
                                                          'x1': line.get('x1'), 'y1': line.get('bottom'),
                                                          'page_number': page.page_number})

            else:
                if line.get('x0') > education_block_start.get('x0') + 10:
                    imaginary_lines[f'{ed_page}'].append({'x0': education_block_start.get('x0'), 'y0': line.get('top'),
                                                          'x1': line.get('x1'), 'y1': line.get('bottom'),
                                                          'page_number': page.page_number})

    imaginary_lines[f'{education_pages[0]}'].insert(0, education_block_start) # Засовываем на место первого элемента начало блока
    imaginary_lines[f'{education_pages[-1]}'].append(education_block_end) # Засовываем на место последнего элемента конец блока

    print(imaginary_lines)

    # Получаем блоки текста
    is_tear = False
    education_blocks = []
    for ed_page in education_pages:
        current_imaginary_lines = imaginary_lines.get(f'{ed_page}')
        for current_index, imaginary_line in enumerate(current_imaginary_lines):
            if not imaginary_line.get('isLast', False):
                if is_tear:
                    education_block = pdf.pages[ed_page].crop((0, 0,
                                                               imaginary_line.get('x1'), imaginary_line.get('y1')))
                    is_tear = False
                    education_blocks.append(education_block)
                try:
                    y1 = current_imaginary_lines[current_index + 1].get('y1')
                except IndexError:
                    is_tear = True
                    y1 = pdf.pages[ed_page].height
                education_block = pdf.pages[ed_page].crop((imaginary_line.get('x0'), imaginary_line.get('y0'),
                                                           imaginary_line.get('x1'), y1))
                education_blocks.append(education_block)
    return education_blocks


def find_words_in_line():
    with pdfplumber.open(FILE_PATH) as pdf:
        first_page = pdf.pages[0]
        lines = first_page.lines
        height = lines[0].get('y1') - lines[0].get('y0')
        width = lines[0].get('x1') - lines[0].get('x0')
        first_name_box = first_page.crop((lines[1].get('x0'), (lines[1].get('top') - 20), lines[1].get('x1'), (lines[1].get('bottom') + 100))) # Имя/Фамилия
        words = first_name_box.extract_words()
        im = first_name_box.to_image(resolution=150)
        im.save('f{FILE_PATH}irst_name.png', format="PNG")

        # im = header.to_image(resolution=150)
        # im.save('h{FILE_PATH}eader.png', format="PNG")

        # print(lines)
        # # words = first_page.extract_words()
        # for word in words:
        #     print(word.get("text"))

def main():
    with pdfplumber.open(FILE_PATH) as pdf:
        # name = find_name(pdf)
        # gender = find_gender(pdf)
        # find_education(pdf)
        res = find_text_in_document(pdf)
        print(res)

main()
