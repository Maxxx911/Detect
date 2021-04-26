import pdfplumber

FILE_NAME = 'External.pdf' #External_abdula.pdf - 2oi
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
            return {'text': text.replace(field, ""), 'coordinates': {'x1': word.get('x1'), 'x0': word.get('x0'),
                                                                     'top': word.get('top'),
                                                                     'bottom': word.get('bottom')}}


def detect_text_to_block_with_coordinates(block, coordinates):
    words = block.extract_words(use_text_flow=True, keep_blank_chars=True)
    for word in words:
        if word.get('x0') == coordinates.get('x0'):
            return word


def get_count_of_text(block, field):
    words = block.extract_words(use_text_flow=True, keep_blank_chars=True)
    count = 0
    for word in words:
        text = word.get('text')
        if text.find(field) != -1:
            count += 1
    return count


def find_text_in_document(pdf):
    education_fields = ['Education/Qualification/Training', 'Start Date', 'Field of study', 'Education (degree)',
                        'Training completed', 'Relevant training completed']
    person_name = detect_text_to_block('First Name', pdf.pages[0])
    person_last_name = detect_text_to_block('Family/Last Name', pdf.pages[0])
    gender = detect_text_to_block('Gender', pdf.pages[0])
    geo = detect_text_to_block("WHO geoical distributionlist", pdf.pages[0])
    if geo is None:
        geo = detect_text_to_block("WHO geographical distribution list", pdf.pages[0])
    educations = []
    education_blocks = find_education(pdf)
    for block in education_blocks:
        education_component = {}
        if block.get('is_tear'):
            # Найти по координатом текст
            empty_fields = list(filter(lambda value: value[1].get('text') == '', educations[-1].items()))
            for em_f in empty_fields:
                detected_text = detect_text_to_block_with_coordinates(block.get('education_block'), dict(em_f[1])
                                                                      .get('coordinates'))
                if detected_text is not None:
                    education_component[em_f[0]] = detected_text
        for education_field in education_fields:
            detected_text = detect_text_to_block(education_field, block.get('education_block'))
            if detected_text is not None:
                education_component[education_field] = detected_text
        # if education_component:
        if block.get('is_tear'):
            # Обновление того что нашло
            old_value = educations[-1]
            old_value.update(education_component)
        else:
            educations.append(education_component)
    return {'person_name': person_name, 'person_last_name': person_last_name, 'gender': gender, 'education': educations,
            'geo': geo}


WORK_EXPERIENCE_START = None


def find_education(pdf):
    education_text = 'Education, Qualification and Training'
    work_exp_text = 'Work Experience'
    education_block_start = {}
    education_block_end = {}
    count_start = 0
    count_end = 0
    # Находим начало и конец блока
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
                    education_blocks.append({'education_block': education_block, 'is_tear': True})
                try:
                    y1 = current_imaginary_lines[current_index + 1].get('y1')
                except IndexError:
                    is_tear = True
                    y1 = pdf.pages[ed_page].height
                education_block = pdf.pages[ed_page].crop((imaginary_line.get('x0'), imaginary_line.get('y0'),
                                                           imaginary_line.get('x1'), y1))
                education_blocks.append({'education_block': education_block, 'is_tear': False})
    return education_blocks


def detect_work_experience_blocks(pdf):
    block_end_text = 'Cover Letter'
    block_start_text = 'Work Experience'
    work_block_start = {}
    work_block_end = {}
    count_start = 0
    count_end = 0
    for page in pdf.pages:
        lines = page.lines
        for line in lines:
            x0 = line.get('x0')
            top = line.get('top') - 20
            x1 = line.get('x1') + 1
            bottom = line.get('bottom')
            work_block = page.crop((x0, top, x1, bottom))
            try:
                text = work_block.extract_text().replace('\n', ' ')
                if text == block_start_text:
                    count_start += 1
                    # work_block.to_image().save('work_start_block.png', format='png')
                    work_block_start = {'x0': x0, 'y0': top + 20, 'x1': x1, 'y1': bottom,
                                             'page_number': page.page_number}
                elif text == block_end_text:
                    count_end += 1
                    # work_block.to_image().save('work_end_block.png', format='png')

                    work_block_end = {'x0': x0, 'y0': top, 'x1': x1, 'y1': bottom - 20,
                                           'page_number': page.page_number, 'isLast': True}
            except Exception:
                pass
    work_pages = [*range(work_block_start.get('page_number') - 1, work_block_end.get('page_number'))]
    print(work_pages)
    work_exp_count = 1
    work_block_in_page = []
    # Обнаружение кол-во work exp на странице
    for w_page in work_pages:
        count = get_count_of_text(pdf.pages[w_page], f'Work Experience')
        if w_page == work_pages[0]:
            count -= 1
        work_block_in_page.append({'page': w_page, 'count': count})
    coordinates = []
    # Получение координат начала блока
    for work_count in work_block_in_page:
        for i in range(0, work_count.get('count')):
            text = detect_text_to_block(f'Work Experience {work_exp_count}', pdf.pages[work_count.get('page')])
            if text is not None:
                if len(coordinates) > 0:
                    coordinates[-1].update({'end': {'coordinates': text.get('coordinates'),
                                                    'page': work_count.get('page')}})
                work_exp_count += 1
                coordinates.append({'start': {'coordinates': text.get('coordinates'),
                                              'page': work_count.get('page')}})
                coor = text.get('coordinates')
                # pdf.pages[work_count.get('page')].crop((coor.get('x0'), coor.get('top'), coor.get('x1'), coor.get('bottom')))\
                #     .to_image().save(f'START_BLOCK_{work_count.get("page")}_NUMBER_work_exp_count.png', format="PNG")
    end_top = work_block_end.get('y0')
    end_x0 = work_block_end.get('x0')
    end_x1 = work_block_end.get('x1')
    end_bottom = work_block_end.get('y1') + 1
    coordinates[-1].update({'end': { 'coordinates':{"x0": end_x0, 'x1': end_x1, 'top': end_top, 'bottom': end_bottom},
                                    'page': work_block_end.get('page_number') - 1}})
    # Находим блоки с работрй
    crop_blocks = []
    header_height = pdf.pages[0].hyperlinks[0].get('bottom') + 10 # Координата в bottom спецификации заглавия страницы

    for work_number, block in enumerate(coordinates):
        block_coordinates = []
        start_page = block.get('start').get('page')
        end_page = block.get('end').get('page')
        block_pages = [*range(start_page, end_page + 1)]
        for block_page in block_pages:
            y0 = None
            y1 = None
            x0 = 0
            x1 = pdf.pages[start_page].width
            page = block_page
            if block_page == start_page:
                y0 = block.get('start').get('coordinates').get('top')
            if block_page == end_page:
                y1 = block.get('end').get('coordinates').get('bottom')
            if y0 is None:
                y0 = header_height
            if y1 is None:
                y1 = pdf.pages[start_page].height
            block_coordinates.append({'page': page, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1})
        crop_blocks.append({'coordinates': block_coordinates})
    # Parsing
    # Job Title плохое поле, т.к оно есть и в шапке страницы, варант убирать шапку
    field_to_extracts = ['Key Achievements', 'Start Date', 'End Date', 'Job Title']
    titles = []
    for crop_bloc in crop_blocks:
        title = {}
        for field_to_extract in field_to_extracts:
            empty_fields = None
            for coord in crop_bloc.get('coordinates'):
                if empty_fields is not None:
                    word = detect_text_to_block_with_coordinates(pdf.pages[coord.get('page')],
                                                                 empty_fields.get('coordinates'))
                    title[empty_fields.get('field_to_extract')] = word
                else:
                    word = detect_text_to_block(field_to_extract, pdf.pages[coord.get('page')].crop((coord.get('x0'),
                                                                                      coord.get('y0'),
                                                                                      coord.get('x1'),
                                                                                      coord.get('y1'))))
                if word is not None:
                    if word.get('text') == '':
                        empty_fields = {'field_to_extract': field_to_extract, 'coordinates': word.get('coordinates')}
                    else:
                        title[field_to_extract] = word
                        break
        titles.append(title)
    return titles


def main():
    # with pdfplumber.open(FILE_PATH) as pdf:
    #     # name = find_name(pdf)
    #     # gender = find_gender(pdf)
    #     # find_education(pdf)
    #     res = find_text_in_document(pdf)
    #     res = detect_work_experience_blocks(pdf)
    #     # print(res)
    #     wr = detect_work_experience_blocks(pdf)
    #     res = { 'work_experience': wr, **res}
    #     print(wr)
    from detect import DetectText
    import datetime
    delta = datetime.datetime.now()
    r = DetectText(FILE_PATH).find_blocks_coordinates([{'start_block_text': 'Education, Qualification and Training',
                                                        'end_block_text': 'Work Experience',
                                                        'block_name': 'Education'},
                                                       ])
    print(r)
    r = DetectText(FILE_PATH).find_blocks_coordinates([{'start_block_text': 'Work Experience',
                                                        'end_block_text': 'Cover Letter',
                                                        'block_name': 'Work'},
                                                       ])
    print(r)
    r = DetectText(FILE_PATH).find_blocks_coordinates([{'start_block_text': 'Candidate Personal Information',
                                                        'end_block_text': 'Candidate Personal Information',
                                                        'block_name': 'Person Infromation'},
                                                       ])
    print((delta - datetime.datetime.now()).seconds)
main()
