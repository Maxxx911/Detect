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

    def detect_education_text(self, education_block_start, education_block_end):
        education_pages = [*range(education_block_start.get('page_number') - 1, education_block_end.get('page_number'))]
        # Чертим мнимые линии
        imaginary_lines = {}
        for ed_page in education_pages:
            page = self.pdf.pages[ed_page]
            imaginary_lines[f'{ed_page}'] = []
            for line in page.lines:
                if ed_page == education_block_end.get('page_number') - 1:
                    if education_block_end.get('y0') > line.get('top') and line.get('x0') > education_block_start.get(
                            'x0') + 10:
                        imaginary_lines[f'{ed_page}'].append(
                            {'x0': education_block_start.get('x0'), 'y0': line.get('top'),
                             'x1': line.get('x1'), 'y1': line.get('bottom'),
                             'page_number': page.page_number})

                else:
                    if line.get('x0') > education_block_start.get('x0') + 10:
                        imaginary_lines[f'{ed_page}'].append(
                            {'x0': education_block_start.get('x0'), 'y0': line.get('top'),
                             'x1': line.get('x1'), 'y1': line.get('bottom'),
                             'page_number': page.page_number})

        imaginary_lines[f'{education_pages[0]}'].insert(0,
                                                        education_block_start)  # Засовываем на место первого элемента начало блока
        imaginary_lines[f'{education_pages[-1]}'].append(
            education_block_end)  # Засовываем на место последнего элемента конец блока

