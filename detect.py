import pdfplumber


class DetectText:
    education_block_start_text = 'Education, Qualification and Training'
    education_block_end_text = 'Work Experience'
    work_experience_start_text = education_block_end_text
    work_experience_end_text = 'Cover Letter'
    person_information_text = 'Candidate Personal Information'

    def __init__(self, file_path):
        self.pdf = pdfplumber.open(file_path)

    @staticmethod
    def check_is_full_bucket(bucket):
        bucket_length = len(bucket)
        for bucket_element in bucket.values():
            if bool(bucket_element.get('block_start')) and bool(bucket_element.get('block_end')):
                bucket_length -= 1
        return bucket_length == 0

    @staticmethod
    def get_empty_bucket(blocks_to_find):
        bucket_storage = {}
        for block in blocks_to_find:
            bucket_storage[block.get('block_name')] = {'block_start': {}, 'block_end': {}}
        return bucket_storage

    def find_blocks_coordinates(self, blocks_to_find):
        cvs_blocks_coordinates = []
        bucket_storage = self.get_empty_bucket(blocks_to_find)
        for page in self.pdf.pages:
            if self.check_is_full_bucket(bucket_storage):
                cvs_blocks_coordinates.append(bucket_storage)
                bucket_storage = self.get_empty_bucket(blocks_to_find)
            for block_to_find in blocks_to_find:
                block_name = block_to_find.get('block_name')
                for line in page.lines:
                    x0 = line.get('x0')
                    y0 = line.get('top') - 20  # Чуть выше линиии, т.к. над линией название блока
                    x1 = line.get('x1') + 1  # Нужно добавлять единицу, т.к. это линия и не получится взять область
                    y1 = line.get('bottom')
                    block = page.crop((x0, y0, x1, y1))
                    try:
                        detected_text = block.extract_text().replace('\n', '')
                        if detected_text == block_to_find.get('start_block_text'):
                            # block.to_image().save('start_block.png', format='png')
                            bucket_storage[block_name]['block_start'] = {'x0': x0, 'y0': y0 + 20, 'x1': x1, 'y1': y1,
                                                                         'page_number': page.page_number}
                        if detected_text == block_to_find.get('end_block_text'):
                            # block.to_image().save('end_block.png', format='png')
                            bucket_storage[block_name]['block_end'] = {'x0': x0, 'y0': y0 + 20, 'x1': x1, 'y1': y1,
                                                                       'page_number': page.page_number, 'is_end': True}
                    except Exception as e:
                        print(e)  # TODO изменить на лог
        return cvs_blocks_coordinates

    @staticmethod
    def detect_text(block, field):
        words = block.extract_words(use_text_flow=True, keep_blank_chars=True)
        for word in words:
            text = word.get('text')
            if text.find(field) != -1:
                return {'text': text.replace(field, ""), 'coordinates': {'x1': word.get('x1'), 'x0': word.get('x0'),
                                                                         'y0': word.get('top'),
                                                                         'y1': word.get('bottom')}}

    @staticmethod
    def detect_text_with_coordinates(block, coordinates):
        words = block.extract_words(use_text_flow=True, keep_blank_chars=True)
        for word in words:
            if word.get('x0') == coordinates.get('x0'):
                return word

    @staticmethod
    def update_coordinates(coordinates, line, ed_page):
        if (len(coordinates)) > 0:
            coordinates[-1].update({'end': {'coordinates': {'x0': 0,
                                                            'y0': line.get('top'),
                                                            'x1': line.get('x1'),
                                                            'y1': line.get('bottom')},
                                            'page': ed_page}})
        coordinates.append({'start': {'coordinates': {'x0': 0,
                                                      'y0': line.get('top'),
                                                      'x1': line.get('x1'),
                                                      'y1': line.get('bottom')},
                                      'page': ed_page}})


    # TODO заменить получение линий, с помощью текста(С линия какая-то беда(не нашло одну из линий)
    # После замены проверить работу с на WE, все должно работать
    def detect_education_blocks(self, education_block_start, education_block_end):
        education_pages = [*range(education_block_start.get('page_number') - 1, education_block_end.get('page_number'))]
        coordinates = []
        education_block_line_start_y0 = education_block_start.get('y0')
        education_block_line_start_x0 = education_block_start.get('x0') + 10
        education_block_line_end_y0 = education_block_end.get('y0')
        for ed_page in education_pages:
            page = self.pdf.pages[ed_page]
            is_start = ed_page == (education_block_start.get('page_number')) - 1
            is_end = ed_page == (education_block_end.get('page_number')) - 1
            for line in page.lines:
                # Если линия не имеет большего отступа от начала блока
                if line.get('x0') < education_block_line_start_x0:
                    continue
                # Блок с education полностью на одной странице
                if is_end and is_start:
                    if education_block_line_start_y0 < line.get('top') < education_block_line_end_y0:
                        self.update_coordinates(coordinates, line, ed_page)
                # Блок на нескольких страницах и сейчас на первой
                elif is_start:
                    if education_block_line_start_y0 < line.get('top'):
                        self.update_coordinates(coordinates, line, ed_page)
                # Блок на нескольких страницах и сейчас на последней
                elif is_end:
                    if line.get('top') < education_block_line_end_y0:
                        self.update_coordinates(coordinates, line, ed_page)
                # Если сейчас страница между началом и концом
                else:
                    self.update_coordinates(coordinates, line, ed_page)
        end_top = education_block_end.get('y0')
        end_x0 = 0
        end_x1 = education_block_end.get('x1')
        end_bottom = education_block_end.get('y1') + 1
        coordinates[-1].update(
            {'end': {'coordinates': {"x0": end_x0, 'x1': end_x1, 'y0': end_top, 'y1': end_bottom},
                     'page': education_block_end.get('page_number') - 1}})
        return coordinates

    def detect_crop_area(self, blocks):
        cropped_blocks = []
        header_height = self.pdf.pages[0].hyperlinks[0].get(
            'bottom') + 10  # Координата в bottom спецификации заглавия страницы
        for block in blocks:
            block_coordinates = []
            block_page_start = block.get('start').get('page')
            block_page_end = block.get('end').get('page')
            block_pages = [*range(block_page_start, block_page_end + 1)]
            for block_page in block_pages:
                y0 = None
                y1 = None
                x0 = 0
                x1 = self.pdf.pages[block_page_start].width
                if block_page == block_page_start:
                    y0 = block.get('start').get('coordinates').get('y0')
                if block_page == block_page_end:
                    y1 = block.get('end').get('coordinates').get('y1')
                if y0 is None:
                    y0 = header_height
                if y1 is None:
                    y1 = self.pdf.pages[block_page].height
                block_coordinates.append({'page': block_page, 'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1})
            cropped_blocks.append({'coordinates': block_coordinates})
        return cropped_blocks

    def detect_fields(self, cropped_blocks, fields):
        results = []
        for crop_bloc in cropped_blocks:
            extracted_fields = {}
            for field in fields:
                empty_fields = None
                for coord in crop_bloc.get('coordinates'):
                    if empty_fields is not None:
                        word = self.detect_text_with_coordinates(self.pdf.pages[coord.get('page')],
                                                                 empty_fields.get('coordinates'))
                        extracted_fields[empty_fields.get('field_to_extract')] = word
                    else:
                        word = self.detect_text(field, self.pdf.pages[coord.get('page')].crop((coord.get('x0'),
                                                                                               coord.get('y0'),
                                                                                               coord.get('x1'),
                                                                                               coord.get('y1'))))
                    if word is not None:
                        if word.get('text') == '':
                            empty_fields = {'field_to_extract': field,
                                            'coordinates': word.get('coordinates')}
                        else:
                            extracted_fields[field] = word
                            break
            results.append(extracted_fields)
        return results

    def extract_education(self, blocks, fields):
        cropped_area = self.detect_crop_area(blocks)
        return self.detect_fields(cropped_area, fields)
