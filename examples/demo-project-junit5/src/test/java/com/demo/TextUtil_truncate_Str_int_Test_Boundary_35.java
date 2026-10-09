package com.demo;

import com.demo.TextUtil;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class TextUtil_truncate_Str_int_Test_Boundary_35 {


    @Test
    public void testTruncateWithNullString() {
        String result = TextUtil.truncate(null, 5);
        Assertions.assertNull(result, "Truncating a null string should return null");
    }

}
